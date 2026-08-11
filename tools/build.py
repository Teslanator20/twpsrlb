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


def main():
    raw = json.load(open(os.path.join(DATA, "counters.json")))

    bosses = []
    tally = {"solo": collections.Counter(), "team": collections.Counter()}
    top1 = {"solo": collections.Counter(), "team": collections.Counter()}
    points = {"solo": collections.Counter(), "team": collections.Counter()}

    for boss_id in sorted(raw, key=lambda b: (dex_num(b), b)):
        entry = {
            "id": boss_id,
            "name": pokemon_name(boss_id),
            "num": dex_num(boss_id),
            "types": types_of(boss_id),
        }
        for mode in ("solo", "team"):
            lst = raw[boss_id].get(mode)
            if not lst:
                entry[mode] = None
                continue
            entry[mode] = [
                {
                    "id": c["pokemonId"],
                    "name": pokemon_name(c["pokemonId"]),
                    "estimator": c["estimator"],
                    "moves": "%s / %s" % (move_name(c["fastMove"]), move_name(c["chargedMove"])),
                }
                for c in lst
            ]
            for rank, c in enumerate(lst):
                tally[mode][c["pokemonId"]] += 1
                points[mode][c["pokemonId"]] += 5 - rank
                if rank == 0:
                    top1[mode][c["pokemonId"]] += 1
        bosses.append(entry)

    def ranking(mode):
        rows = []
        for pid, count in tally[mode].most_common():
            rows.append(
                {
                    "id": pid,
                    "name": pokemon_name(pid),
                    "count": count,
                    "first": top1[mode][pid],
                    "points": points[mode][pid],
                    "types": types_of(pid),
                }
            )
        rows.sort(key=lambda r: (-r["count"], -r["points"], r["name"]))
        return rows

    covered = {m: sum(1 for b in bosses if b[m]) for m in ("solo", "team")}
    missing = [
        {"id": b["id"], "name": b["name"], "mode": m}
        for b in bosses for m in ("solo", "team") if not b[m]
    ]

    data = {
        "generated": datetime.date.today().isoformat(),
        "bosses": bosses,
        "ranking": {"solo": ranking("solo"), "team": ranking("team")},
        "covered": covered,
        "missing": missing,
    }
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "data.json"), "w") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    print("Bosse: %d | solo: %d | team: %d | fehlend: %d"
          % (len(bosses), covered["solo"], covered["team"], len(missing)))
    print("Top 5 solo:", [(r["name"], r["count"]) for r in data["ranking"]["solo"][:5]])
    print("Top 5 team:", [(r["name"], r["count"]) for r in data["ranking"]["team"][:5]])
    return data


if __name__ == "__main__":
    main()
