from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.error
import ssl
import time

API_BASE = "https://api.wynncraft.com/v3"
_rate_remaining = 50
_rate_reset_at = 0

# Some serverless environments need a default SSL context
ctx = ssl.create_default_context()

def api_get(url):
    global _rate_remaining, _rate_reset_at
    if _rate_remaining <= 2:
        wait = max(0, _rate_reset_at - time.time()) + 0.5
        if wait > 0:
            time.sleep(wait)
    for attempt in range(3):
        req = urllib.request.Request(url, headers={"User-Agent": "TWP-SR-Checker/1.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            _rate_remaining = int(resp.headers.get("ratelimit-remaining", "50"))
            reset_sec = int(resp.headers.get("ratelimit-reset", "30"))
            _rate_reset_at = time.time() + reset_sec
            body = resp.read()
            return 200, json.loads(body)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                reset_sec = int(e.headers.get("ratelimit-reset", "30"))
                _rate_reset_at = time.time() + reset_sec
                _rate_remaining = 0
                time.sleep(reset_sec + 1)
                continue
            if e.code == 404:
                return 404, None
            return e.code, None
        except Exception as e:
            return 0, str(e)
    return 429, None

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(content_length)) if content_length else {}
        names = body.get("names", [])

        results = []
        errors = []
        start = time.time()
        checked = 0

        for name in names:
            if time.time() - start > 50:
                break
            code, data = api_get(f"{API_BASE}/player/{name}")
            checked += 1
            if code == 200 and data is not None:
                na_sr = data.get("ranking", {}).get("NASrPlayers")
                if na_sr is not None:
                    guild = data.get("guild")
                    pfx = guild.get("prefix", "?") if guild else "N/A"
                    raids_data = data.get("globalData", {}).get("raids", {})
                    unknown_raids = raids_data.get("list", {}).get("unknown", 0)
                    total_raids = raids_data.get("total", 0)
                    results.append({
                        "name": data.get("username", name),
                        "guild": pfx,
                        "NASrPlayers": na_sr,
                        "unknownRaids": unknown_raids,
                        "totalRaids": total_raids,
                    })
            elif code != 404:
                errors.append({"name": name, "code": code, "detail": str(data)[:100] if data else ""})

        resp_body = {
            "results": results,
            "checked": checked,
            "total": len(names),
            "elapsed": round(time.time() - start, 1),
        }
        if errors:
            resp_body["errors"] = errors[:5]

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(resp_body).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
