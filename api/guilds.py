from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import time

API_BASE = "https://api.wynncraft.com/v3"

GUILD_PREFIXES = [
    "Zamn", "SEQ", "Aeq", "HSP", "ETKW", "ANO",
    "AVO", "ESI", "Nia", "Ico", "Eden",
    "SOVR", "PUN", "BFS", "TAq", "PROF",
    "Frmr", "caelxsti", "1n_L",
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

def fetch_json(url):
    try:
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=10)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, None
    except Exception:
        return 500, None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        """Fetch all guild member names + staff names."""
        all_names = []
        guilds_info = []

        for prefix in GUILD_PREFIXES:
            code, data = fetch_json(f"{API_BASE}/guild/prefix/{prefix}")
            if code != 200 or data is None:
                continue
            name = data.get("name", prefix)
            pfx = data.get("prefix", prefix)
            member_data = data.get("members", {})
            count = 0
            for rank in ["owner", "chief", "strategist", "captain", "recruiter", "recruit"]:
                for mname in member_data.get(rank, {}):
                    all_names.append(mname)
                    count += 1
            guilds_info.append({"prefix": pfx, "name": name, "members": count})
            time.sleep(0.3)

        # Add staff not already in guild list
        name_set = set(all_names)
        for s in STAFF_NAMES:
            if s not in name_set:
                all_names.append(s)

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps({
            "names": all_names,
            "guilds": guilds_info,
            "total": len(all_names),
        }).encode())
