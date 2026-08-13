#!/usr/bin/env python3
"""Baut data/bosses.json: alle legendaeren und mysterioesen Raidbosse mit ihrer Raid-Stufe.

Beruecksichtigt werden nur Bosse, die tatsaechlich schon in Raids aufgetreten sind -
also die aktuellen Listen und die Legacy-Listen, nicht die FUTURE-Listen mit noch
unveroeffentlichten Bossen.
"""
import json
import os
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

API = "https://fight.pokebattler.com"
RARITIES = {"POKEMON_RARITY_LEGENDARY", "POKEMON_RARITY_MYTHIC"}

# API-Stufe -> Pokebattler-Listen, die darauf abgebildet werden. Reihenfolge = Prioritaet:
# ein Boss, der in mehreren Listen steht, bekommt die erste passende Stufe.
# rare_only=True beschraenkt auf legendaere und mysterioese Pokemon; Mega-Raids nehmen
# wir vollstaendig mit, dort ist die Mega-Form selbst das Auswahlkriterium.
GROUPS = [
    ("RAID_LEVEL_5", ("RAID_LEVEL_5", "RAID_LEVEL_5_LEGACY"), True),
    ("RAID_LEVEL_MEGA_5", ("RAID_LEVEL_MEGA_5", "RAID_LEVEL_MEGA_5_LEGACY"), True),
    ("RAID_LEVEL_ELITE", ("RAID_LEVEL_ELITE", "RAID_LEVEL_ELITE_LEGACY"), True),
    ("RAID_LEVEL_MEGA", ("RAID_LEVEL_MEGA", "RAID_LEVEL_MEGA_LEGACY"), False),
]

# Formen, die nur Alias einer anderen ID in derselben Liste sind.
ALIASES = {"TORNADUS", "THUNDURUS", "LANDORUS", "ENAMORUS"}
# Krypto-Bosse gehoeren in eine eigene Auswertung, hier nicht mitzaehlen.
EXCLUDE_SUFFIX = ("_SHADOW_FORM",)


def fetch(path):
    req = urllib.request.Request(API + path, headers={"User-Agent": "counter-stats/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.load(resp)


def main():
    raids = fetch("/raids")["tiers"]
    pokemon = {p["pokemonId"]: p for p in fetch("/pokemon")["pokemon"]}
    by_list = {t["tier"]: {r["pokemon"] for r in t["raids"]} for t in raids}

    assigned = {}
    for tier, lists, rare_only in GROUPS:
        for name in lists:
            for pid in sorted(by_list.get(name, ())):
                if pid in assigned or pid in ALIASES:
                    continue
                if pid.endswith(EXCLUDE_SUFFIX):
                    continue
                if rare_only and pokemon.get(pid, {}).get("rarity") not in RARITIES:
                    continue
                assigned[pid] = tier

    order = {tier: i for i, (tier, _, _) in enumerate(GROUPS)}
    bosses = [
        {"id": pid, "tier": tier}
        for pid, tier in sorted(assigned.items(), key=lambda kv: (order[kv[1]], kv[0]))
    ]

    # Ein abgespeckter Pokedex reicht der Auswertung.
    keep = {"pokemonId", "type", "type2", "rarity", "pokedex"}
    slim = {"pokemon": [{k: v for k, v in p.items() if k in keep} for p in pokemon.values()]}

    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, "bosses.json"), "w") as fh:
        json.dump(bosses, fh, indent=1)
    with open(os.path.join(DATA, "pokemon.json"), "w") as fh:
        json.dump(slim, fh)

    for tier, _, _ in GROUPS:
        ids = [b["id"] for b in bosses if b["tier"] == tier]
        print("%-22s %2d  %s" % (tier, len(ids), ", ".join(ids) if len(ids) < 15 else "…"))
    print("gesamt: %d" % len(bosses))


if __name__ == "__main__":
    main()
