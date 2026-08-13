#!/usr/bin/env python3
"""Holt fuer jeden legendaeren Raid-Boss die Counter-Rangliste von Pokebattler.

Zwei Konfigurationen:
  solo  -> numParty=1, friendLevel=FRIENDSHIP_LEVEL_0   (keine Team-Power, kein Freundschaftsbonus)
  team  -> numParty=2, friendLevel=FRIENDSHIP_LEVEL_4   (Team-Power, bester Freund)
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
API = "https://fight.pokebattler.com"
TOP_N = 30  # Pokebattler liefert 30 Konter; gefiltert wird spaeter in build.py

CONFIGS = {
    "solo": {"numParty": "1", "friendLevel": "FRIENDSHIP_LEVEL_0"},
    "team": {"numParty": "2", "friendLevel": "FRIENDSHIP_LEVEL_4"},
}


def build_url(boss, tier, cfg):
    params = [
        ("sort", "ESTIMATOR"),
        ("weatherCondition", "NO_WEATHER"),
        ("dodgeStrategy", "DODGE_REACTION_TIME"),
        ("aggregation", "AVERAGE"),
        ("randomAssistants", "-1"),
        ("numMegas", "0"),
        ("numParty", cfg["numParty"]),
        ("friendLevel", cfg["friendLevel"]),
    ]
    query = "&".join("%s=%s" % kv for kv in params)
    return (
        "%s/raids/defenders/%s/levels/%s/attackers/levels/40"
        "/strategies/CINEMATIC_ATTACK_WHEN_POSSIBLE/DEFENSE_RANDOM_MC?%s"
        % (API, boss, tier, query)
    )


def fetch(url, attempts=5):
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "counter-stats/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.load(resp)
        except Exception as exc:  # 504 kommt als HTTPError, Timeouts als URLError
            last = exc
            time.sleep(2 ** i)
    raise RuntimeError("fetch failed: %s (%s)" % (url, last))


def top_counters(payload, n=TOP_N):
    """Pokebattler sortiert die Counter aufsteigend (schlechtester zuerst)."""
    defenders = payload["attackers"][0]["randomMove"]["defenders"]
    best = []
    for entry in reversed(defenders[-n:]):
        move = min(entry["byMove"], key=lambda m: m["result"]["estimator"])
        best.append(
            {
                "pokemonId": entry["pokemonId"],
                "estimator": round(move["result"]["estimator"], 4),
                "fastMove": move["move1"],
                "chargedMove": move["move2"],
            }
        )
    return best


def main():
    bosses = json.load(open(os.path.join(DATA, "bosses.json")))
    out_path = os.path.join(DATA, "counters.json")
    results = {}
    if os.path.exists(out_path):
        results = json.load(open(out_path))

    # Fehlschlaege stehen als null in der Datei und werden normalerweise uebersprungen,
    # damit ein Wiederholungslauf nicht jedes Mal in dieselben Timeouts rennt.
    # RETRY_FAILED=1 nimmt sie erneut in Angriff - teure Sims rechnet Pokebattler nach
    # dem ersten 504 im Hintergrund weiter und liefert sie beim naechsten Versuch aus.
    if os.environ.get("RETRY_FAILED"):
        for done in results.values():
            for name in [n for n, v in done.items() if not v]:
                del done[name]

    for entry in bosses:
        boss, tier = entry["id"], entry["tier"]
        results.setdefault(boss, {})
        for name, cfg in CONFIGS.items():
            if name in results[boss]:
                continue
            try:
                data = fetch(build_url(boss, tier, cfg))
                results[boss][name] = top_counters(data)
                print("ok   %-32s %-4s %s" % (boss, name, results[boss][name][0]["pokemonId"]))
            except Exception as exc:
                results[boss][name] = None
                print("FAIL %-32s %-4s %s" % (boss, name, exc))
            json.dump(results, open(out_path, "w"), indent=1)
            sys.stdout.flush()

    missing = [
        (b["id"], c) for b in bosses for c in CONFIGS if not results.get(b["id"], {}).get(c)
    ]
    print("fertig. fehlend: %d" % len(missing))
    for m in missing:
        print("  ", m)


if __name__ == "__main__":
    main()
