#!/usr/bin/env python3
"""Baut aus counters.json die Auswertung + die statische Website."""
import collections
import datetime
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")
OUT = os.environ.get("OUT_DIR", ROOT)

CONST = json.load(open(os.path.join(DATA, "de_constants.json")))
NAMES = CONST["pokemon"]
MOVES = CONST["moves"]
POKEDEX = {p["pokemonId"]: p for p in json.load(open(os.path.join(DATA, "pokemon.json")))["pokemon"]}

REF = re.compile(r"\$t\(constants:(pokemon|moves)\.([A-Z0-9_]+)\)")

SUFFIXES = [
    ("_SHADOW_FORM", "SHADOW_FORM", "prefix"),
    ("_GIGANTAMAX", "GIGANTAMAX", "prefix"),
    ("_PRIMAL", "PRIMAL_FORM", "prefix"),
    ("_MEGA_X", "MEGA_EVO", "mega_x"),
    ("_MEGA_Y", "MEGA_EVO", "mega_y"),
    ("_MEGA", "MEGA_EVO", "prefix"),
]


def resolve(table, key, depth=0):
    """Loest i18n-Referenzen auf und faellt bei Luecken auf Komposition zurueck."""
    if depth > 6:
        return key
    raw = table.get(key)
    if raw is None:
        return None
    return REF.sub(
        lambda m: (resolve(NAMES if m.group(1) == "pokemon" else MOVES, m.group(2), depth + 1)
                   or m.group(2).replace("_", " ").title()),
        raw,
    )


def pokemon_name(pid):
    name = resolve(NAMES, pid)
    if name:
        return name
    for suffix, marker, kind in SUFFIXES:
        if pid.endswith(suffix):
            base = pokemon_name(pid[: -len(suffix)])
            tag = resolve(NAMES, marker) or marker.replace("_", " ").title()
            if kind == "mega_x":
                return "%s-%s X" % (tag, base)
            if kind == "mega_y":
                return "%s-%s Y" % (tag, base)
            return "%s-%s" % (tag, base)
    if pid.endswith("_FORM"):
        return pokemon_name(pid[: -len("_FORM")]) or pid.replace("_", " ").title()
    return pid.replace("_", " ").title()


def move_name(mid):
    return resolve(MOVES, mid) or mid.replace("_FAST", "").replace("_", " ").title()


def types_of(pid):
    p = POKEDEX.get(pid) or {}
    out = []
    for key in ("type", "type2"):
        t = p.get(key)
        if t:
            out.append(
                {
                    "id": t.replace("POKEMON_TYPE_", "").lower(),
                    "name": resolve(CONST["types"], t) or t.replace("POKEMON_TYPE_", "").title(),
                }
            )
    return out


def dex_num(pid):
    return (POKEDEX.get(pid) or {}).get("pokedex", {}).get("pokemonNum", 9999)


def tier_label(tier, pid):
    if tier == "RAID_LEVEL_MEGA_5":
        return "Proto-Raid" if pid.endswith("_PRIMAL") else "Mega-Raid (legendär)"
    if tier == "RAID_LEVEL_MEGA":
        return "Mega-Raid"
    if tier == "RAID_LEVEL_ELITE":
        return "Elite-Raid"
    return "Stufe 5"


def is_mega(pid):
    """Mega-Entwicklungen und Protoformen - in Pokemon GO dieselbe Mechanik."""
    return "_MEGA" in pid or pid.endswith("_PRIMAL")


def is_shadow(pid):
    return pid.endswith("_SHADOW_FORM")


TOP_N = 5
MODES = ("team", "solo")
# Dieselbe Auswertung in drei Zaehltiefen: alle fuenf Plaetze, nur die ersten zwei, nur Platz 1.
DEPTHS = {"top5": 5, "top2": 2, "top1": 1}
# Der Schluessel im Boss-Eintrag je Konfiguration und Angreifer-Pool.
KEYS = {("team", False): "team", ("solo", False): "solo",
        ("team", True): "teamMega", ("solo", True): "soloMega"}
# Jede Auswertung gibt es zweimal: ohne und mit Krypto-Angreifern.
VARIANTS = {"noShadow": False, "withShadow": True}


def select(full, mega, shadows):
    """Die besten TOP_N Konter aus der 30er-Liste, gefiltert nach Pool."""
    picks = []
    for c in full:
        pid = c["pokemonId"]
        if is_mega(pid) != mega or (not shadows and is_shadow(pid)):
            continue
        picks.append(c)
        if len(picks) == TOP_N:
            break
    return picks


def merge(plain, megas):
    """Gesamtvergleich: Megas und Nicht-Megas in einer Reihe, bester Estimator zuerst.

    Die Vereinigung der beiden Pool-Spitzen enthaelt die tatsaechlich besten TOP_N,
    deshalb genuegt es, die zwei fertigen Listen zusammenzulegen.
    """
    return sorted(plain + megas, key=lambda c: c["estimator"])[:TOP_N]


def main():
    raw = json.load(open(os.path.join(DATA, "counters.json")))
    tiers = {b["id"]: b["tier"] for b in json.load(open(os.path.join(DATA, "bosses.json")))}

    def counter(c):
        """Ein Pokemon = ein Eintrag, darunter seine besten Attackensets mit eigenem Estimator."""
        return {
            "id": c["pokemonId"],
            "name": pokemon_name(c["pokemonId"]),
            "estimator": c["estimator"],
            "sets": [
                {
                    "moves": "%s / %s" % (move_name(m["fastMove"]), move_name(m["chargedMove"])),
                    "estimator": m["estimator"],
                }
                for m in c["movesets"]
            ],
        }


    bosses = []
    # tally[variant][depth][key] - je Krypto-Variante, Zaehltiefe und Pool.
    tally, top1, points = {}, {}, {}
    for variant in VARIANTS:
        for store in (tally, top1, points):
            store[variant] = {
                depth: {key: collections.Counter() for key in KEYS.values()}
                for depth in DEPTHS
            }

    for boss_id in sorted(raw, key=lambda b: (dex_num(b), b)):
        tier = tiers.get(boss_id, "RAID_LEVEL_5")
        entry = {
            "id": boss_id,
            "name": pokemon_name(boss_id),
            "num": dex_num(boss_id),
            "types": types_of(boss_id),
            "tier": tier_label(tier, boss_id),
            "special": tier != "RAID_LEVEL_5",
            "picks": {v: {} for v in VARIANTS},
        }
        for variant, shadows in VARIANTS.items():
            for mode in MODES:
                full = raw[boss_id].get(mode)
                pools = {}
                for mega in (False, True):
                    key = KEYS[(mode, mega)]
                    if not full:
                        entry["picks"][variant][key] = None
                        continue
                    pools[mega] = select(full, mega, shadows)
                    entry["picks"][variant][key] = [counter(c) for c in pools[mega]]
                if not full:
                    continue
                # Ohne Megas: Position innerhalb des eigenen Pools.
                key = KEYS[(mode, False)]
                for depth, n in DEPTHS.items():
                    for rank, c in enumerate(pools[False][:n]):
                        pid = c["pokemonId"]
                        tally[variant][depth][key][pid] += 1
                        points[variant][depth][key][pid] += n - rank
                        if rank == 0:
                            top1[variant][depth][key][pid] += 1
                # Megas: Position im Gesamtvergleich. Ein Mega zaehlt nur, wenn es sich
                # auch gegen die Nicht-Megas durchsetzt.
                key = KEYS[(mode, True)]
                overall = merge(pools[False], pools[True])
                for depth, n in DEPTHS.items():
                    for rank, c in enumerate(overall[:n]):
                        pid = c["pokemonId"]
                        if not is_mega(pid):
                            continue
                        tally[variant][depth][key][pid] += 1
                        points[variant][depth][key][pid] += n - rank
                        if rank == 0:
                            top1[variant][depth][key][pid] += 1
        bosses.append(entry)

    def ranking(variant, depth, key):
        rows = [
            {
                "id": pid,
                "name": pokemon_name(pid),
                "count": count,
                "first": top1[variant][depth][key][pid],
                "points": points[variant][depth][key][pid],
                "types": types_of(pid),
            }
            for pid, count in tally[variant][depth][key].items()
        ]
        rows.sort(key=lambda r: (-r["count"], -r["points"], r["name"]))
        return rows

    def mega_ranking(variant, depth):
        """Eine Zeile je Mega, mit beiden Zaehlungen nebeneinander."""
        counts, firsts, pts = tally[variant][depth], top1[variant][depth], points[variant][depth]
        ids = set(counts["teamMega"]) | set(counts["soloMega"])
        rows = [
            {
                "id": pid,
                "name": pokemon_name(pid),
                "types": types_of(pid),
                "team": counts["teamMega"][pid],
                "solo": counts["soloMega"][pid],
                "teamFirst": firsts["teamMega"][pid],
                "soloFirst": firsts["soloMega"][pid],
                "points": pts["teamMega"][pid] + pts["soloMega"][pid],
            }
            for pid in ids
        ]
        rows.sort(key=lambda r: (-(r["team"] + r["solo"]), -r["points"], r["name"]))
        return rows

    # Ob Daten vorliegen, haengt nicht an der Krypto-Variante.
    def has(boss, mode):
        return bool(boss["picks"]["withShadow"][mode])

    covered = {m: sum(1 for b in bosses if has(b, m)) for m in MODES}
    missing = [
        {"id": b["id"], "name": b["name"], "mode": m}
        for b in bosses for m in MODES if not has(b, m)
    ]

    data = {
        "generated": datetime.date.today().isoformat(),
        "bosses": bosses,
        "ranking": {
            variant: {
                depth: {
                    "team": ranking(variant, depth, "team"),
                    "solo": ranking(variant, depth, "solo"),
                    "mega": mega_ranking(variant, depth),
                }
                for depth in DEPTHS
            }
            for variant in VARIANTS
        },
        "covered": covered,
        "missing": missing,
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "data.json"), "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print("Bosse: %d | solo: %d | team: %d | fehlend: %d"
          % (len(bosses), covered["solo"], covered["team"], len(missing)))
    for variant in VARIANTS:
        for depth in DEPTHS:
            print("--- %s / %s" % (variant, depth))
            r = data["ranking"][variant][depth]
            for label in ("team", "solo"):
                print("  %-4s (ohne Megas):" % label,
                      [(x["name"], x["count"]) for x in r[label][:4]])
            print("  Megas:", [(x["name"], x["team"], x["solo"]) for x in r["mega"][:4]])
    return data


if __name__ == "__main__":
    main()
