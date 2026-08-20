#!/usr/bin/env python3
"""Holt fuer jeden Raid-Boss die Counter-Rangliste von Pokebattler.

Sortiert nach TIME - "Time to win assuming infinite number of Pokemon". Diese Zeit ist
die Vergleichsgroesse: mit unbegrenzt vielen Pokemon schafft jeder Angreifer jedes
Boss-Attackenset, unterschiedlich ist nur, wie lange er braucht.

Angreifer auf Level 50. Solche Abfragen liegen selten im Cache und laufen beim ersten
Mal in Pokebattlers 30-Sekunden-Timeout - der Server rechnet aber weiter und liefert sie
beim naechsten Versuch aus. Deshalb zwei Phasen:

  WARMUP=1 python3 tools/scrape.py   # bricht jede Abfrage nach 3 s ab, nur zum Anstossen
  python3 tools/scrape.py            # holt die Ergebnisse ein
  RETRY_FAILED=1 python3 tools/scrape.py   # fuer die Nachzuegler

Das Abbrechen genuegt: die Berechnung laeuft serverseitig weiter.

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
ATTACKER_LEVEL = 50
TOP_N = 30  # Pokebattler liefert 30 Konter; gefiltert wird spaeter in build.py
MOVESETS_N = 3  # je Konter die drei besten Attackensets

CONFIGS = {
    "solo": {"numParty": "1", "friendLevel": "FRIENDSHIP_LEVEL_0"},
    "team": {"numParty": "2", "friendLevel": "FRIENDSHIP_LEVEL_4"},
}


def build_url(boss, tier, cfg):
    params = [
        ("sort", "TIME"),
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
        "%s/raids/defenders/%s/levels/%s/attackers/levels/%d"
        "/strategies/CINEMATIC_ATTACK_WHEN_POSSIBLE/DEFENSE_RANDOM_MC?%s"
        % (API, boss, tier, ATTACKER_LEVEL, query)
    )


# Viele Abfragen sind beim ersten Mal zu teuer und laufen in Pokebattlers 30-Sekunden-
# Timeout. Der Server rechnet danach im Hintergrund weiter, deshalb lohnt sich schnelles
# Scheitern und ein weiterer Durchlauf statt langer Retry-Ketten im selben Lauf.
ATTEMPTS = int(os.environ.get("ATTEMPTS", "2"))


def fetch(url, attempts=None):
    attempts = attempts or ATTEMPTS
    last = None
    for i in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "counter-stats/1.0"})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429:  # gedrosselt - deutlich langsamer weitermachen
                time.sleep(60)
            else:
                time.sleep(2 ** i)
        except Exception as exc:
            last = exc
            time.sleep(2 ** i)
    raise RuntimeError("fetch failed: %s (%s)" % (url, last))


def seconds(result):
    """Time to win in Sekunden - kleiner ist besser."""
    return round(result["effectiveCombatTime"] / 1000.0, 1)


def top_counters(payload, n=TOP_N):
    """Die besten Konter, bester zuerst, je Konter die MOVESETS_N schnellsten Sets.

    Ein Pokemon bleibt ein Eintrag, seine Attackensets stehen darunter.
    """
    defenders = payload["attackers"][0]["randomMove"]["defenders"]
    ranked = sorted(
        defenders,
        key=lambda e: min(m["result"]["effectiveCombatTime"] for m in e["byMove"]),
    )[:n]
    best = []
    for entry in ranked:
        moves = sorted(entry["byMove"], key=lambda m: m["result"]["effectiveCombatTime"])[:MOVESETS_N]
        best.append(
            {
                "pokemonId": entry["pokemonId"],
                "time": seconds(moves[0]["result"]),
                "estimator": round(moves[0]["result"]["estimator"], 4),
                "movesets": [
                    {
                        "fastMove": m["move1"],
                        "chargedMove": m["move2"],
                        "time": seconds(m["result"]),
                        "estimator": round(m["result"]["estimator"], 4),
                    }
                    for m in moves
                ],
            }
        )
    return best


def warmup(bosses, results):
    """Stoesst jede noch fehlende Berechnung an, ohne auf das Ergebnis zu warten."""
    n = 0
    for entry in bosses:
        boss, tier = entry["id"], entry["tier"]
        for name, cfg in CONFIGS.items():
            if results.get(boss, {}).get(name):
                continue
            n += 1
            try:
                req = urllib.request.Request(
                    build_url(boss, tier, cfg), headers={"User-Agent": "counter-stats/1.0"})
                urllib.request.urlopen(req, timeout=3).read(1)
            except Exception:
                pass
            if n % 25 == 0:
                print("angestossen: %d" % n)
                sys.stdout.flush()
    print("Vorwaermen fertig: %d Abfragen angestossen" % n)


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

    if os.environ.get("WARMUP"):
        warmup(bosses, results)
        return

    for entry in bosses:
        boss, tier = entry["id"], entry["tier"]
        results.setdefault(boss, {})
        for name, cfg in CONFIGS.items():
            if name in results[boss]:
                continue
            try:
                data = fetch(build_url(boss, tier, cfg))
                results[boss][name] = top_counters(data)
                top = results[boss][name][0]
                print("ok   %-32s %-4s %-28s %.1f s"
                      % (boss, name, top["pokemonId"], top["time"]))
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
