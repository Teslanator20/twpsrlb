"""TWP SR scanner - checks all guild members + staff for NASrPlayers ranking."""
import urllib.request
import urllib.error
import ssl
import json
import time
import sys
import os

API_BASE = "https://api.wynncraft.com/v3"
DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "na_sr_results.json")
ctx = ssl.create_default_context()

GUILD_PREFIXES = [
    "Zamn", "SEQ", "Aeq", "HSP", "ETKW", "ANO",
    "AVO", "ESI", "Nia", "Ico", "Eden",
    "SOVR", "PUN", "BFS", "TAq", "PROF",
    "Frmr",
]

STAFF_NAMES = [
    "Salted", "Grian", "Jumla", "clx_", "Crunkle", "HeyZeer0",
    "Nepmia", "MowerOfSocks", "Terminated", "Michael", "Imaxe", "Irony",
    "lexnt", "Tealycraft", "Lumia", "Hams", "birb", "LegendMC119",
    "RandomDuckNerd", "KeytarAshes", "Ph8enix", "Deusphage", "keplyr",
    "daeja_vu", "Texilated", "Snerp", "AfroSnail", "FireHeart27",
    "LuxioCat", "KingEggplant", "Plasmatic", "Dragunovi", "LadyNebula",
    "EmeraldsEmerald", "_qe", "Magicmakerman", "Daisukekage",
    "Star__Bright", "That1Strange1Guy", "9o62", "LuCoolUs", "SirRoboB0b",
    "AJlovesgaming19", "LeoCTW", "xSuper_Jx", "Mardeknius", "nicktree",
    "olinus10", "AngieTape", "Greyborne", "wisedrag", "touhoku",
    "DrBracewell", "altamoth", "HarryOtterTM", "Wetherspoon", "Zetrokzebro",
    "Peakerchu", "GamerHD0106", "Samsam101", "zenythia", "SugVon",
    "RealUnicornKitty", "fishcute", "TarotVTuber", "Monkeyhue", "kyrkis",
    "Hypochloride", "HalfCat", "Rythew", "Toy", "Chigo",
    "NagisaStreams", "EchoingWinds", "Jbip", "Emil", "PeterMarius",
    "Pianoplayer1", "andreasmachtdas", "Monkeykapaa", "block36_", "Winteria",
    "JerryStuffRo", "ElectricCurrent", "Selvut283", "Morange", "Autosmord",
    "btdmaster", "Lemon", "astralproject", "Cal_and_Ben", "linnyflower",
    "FriesBeforeGuyz", "ImNotYourAEB", "Vaky", "CattenXP", "Unbeatable",
    "Ezoey_c", "Fiqshy", "asinasura", "Steamed_Kalamari", "punscake",
    "Enderclaw", "cal_and_ben", "_juliqn", "AmbassadorDazz", "BoltyBlud",
    "Dream", "Fiery_Mystery", "Fowlgorithm", "Hansby", "ItzAzura",
    "JohnBleu", "JokeOfJoke", "Julinho", "LesbianDream", "Lunatic_Lady",
    "QwertyKat14", "RafaelGomes", "Rexshell", "SixL__", "Soulbound",
    "Volkzz101", "yuliqn", "Naraka00", "MilkeeW", "Jekie",
]

_rate_remaining = 50
_rate_reset_at = 0

def api_get(url):
    global _rate_remaining, _rate_reset_at
    if _rate_remaining <= 2:
        wait = max(0, _rate_reset_at - time.time()) + 0.5
        if wait > 0:
            print(f"    Waiting {wait:.0f}s for rate limit reset...", flush=True)
            time.sleep(wait)
    for attempt in range(5):
        req = urllib.request.Request(url, headers={"User-Agent": "TWP-SR-Scanner/1.0"})
        try:
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            _rate_remaining = int(resp.headers.get("ratelimit-remaining", "50"))
            reset_sec = int(resp.headers.get("ratelimit-reset", "30"))
            _rate_reset_at = time.time() + reset_sec
            return 200, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            if e.code == 429:
                reset_sec = int(e.headers.get("ratelimit-reset", "30"))
                _rate_reset_at = time.time() + reset_sec
                _rate_remaining = 0
                print(f"    429 - waiting {reset_sec + 1}s...", flush=True)
                time.sleep(reset_sec + 1)
                continue
            if e.code == 404:
                return 404, None
            return e.code, None
        except Exception as e:
            print(f"    Error: {e}", flush=True)
            return 0, None
    return 429, None

def check_player(name):
    code, data = api_get(f"{API_BASE}/player/{name}")
    if code != 200 or data is None:
        return None
    na_sr = data.get("ranking", {}).get("NASrPlayers")
    if na_sr is not None:
        guild = data.get("guild")
        pfx = guild.get("prefix", "?") if guild else "N/A"
        unknown_raids = data.get("globalData", {}).get("raids", {}).get("list", {}).get("unknown", 0)
        return {"name": data.get("username", name), "guild": pfx, "NASrPlayers": na_sr, "unknownRaids": unknown_raids}
    return None

def check_players(names, label, results):
    total = len(names)
    print(f"Checking {total} {label}...", flush=True)
    for i, name in enumerate(names, 1):
        r = check_player(name)
        if r:
            results[r["name"]] = r
            print(f"  [{i}/{total}] {r['name']} ({r['guild']}) - #{ r['NASrPlayers']}", flush=True)
        elif i % 100 == 0:
            print(f"  [{i}/{total}] checking...", flush=True)

def save_results(results):
    sorted_results = sorted(results.values(), key=lambda x: x["NASrPlayers"])
    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "guilds_checked": GUILD_PREFIXES,
        "staff_checked": len(STAFF_NAMES),
        "ranked_players": len(sorted_results),
        "results": sorted_results,
    }
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n{len(sorted_results)} ranked players. Saved.", flush=True)

def run_top():
    try:
        with open(DATA_FILE) as f:
            existing = json.load(f)
        known = [r["name"] for r in existing.get("results", [])]
    except FileNotFoundError:
        print("No existing data, running full scan.", flush=True)
        return run_all()
    print(f"Refreshing {len(known)} known players...", flush=True)
    results = {}
    check_players(known, "known players", results)
    save_results(results)

def run_all():
    results = {}
    print("Fetching guilds...", flush=True)
    all_members = []
    for prefix in GUILD_PREFIXES:
        code, data = api_get(f"{API_BASE}/guild/prefix/{prefix}")
        if code != 200 or data is None:
            print(f"  [{prefix}] FAILED: {code}", flush=True)
            continue
        name = data.get("name", prefix)
        pfx = data.get("prefix", prefix)
        member_data = data.get("members", {})
        count = 0
        for rank in ["owner", "chief", "strategist", "captain", "recruiter", "recruit"]:
            for mname in member_data.get(rank, {}):
                all_members.append(mname)
                count += 1
        print(f"  [{pfx}] {name}: {count} members", flush=True)

    check_players(all_members, "guild members", results)
    staff_to_check = [n for n in STAFF_NAMES if n not in results]
    check_players(staff_to_check, "staff", results)
    save_results(results)

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    if mode == "top":
        run_top()
    else:
        run_all()
