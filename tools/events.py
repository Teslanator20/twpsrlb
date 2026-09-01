#!/usr/bin/env python3
"""Baut data/events.json: Event-Kalender und aktuelle Raid-Bosse.

Quelle ist ScrapedDuck, der maschinenlesbare Abzug von Leek Duck:
  events.json  - Events mit Start und Ende
  raids.json   - die Bosse, die *gerade* in Raids stehen

Was dort fehlt, sind tagesgenaue Angaben innerhalb eines mehrtaegigen Events. "Mega
Ascension" steht als ein Block vom 31.08. bis 04.09. drin, obwohl jeden Tag ein anderes
Mega im Raid ist - genau die Information, die man braucht. Die traegt data/events_extra.json
von Hand nach; siehe CLAUDE.md.

Bosse werden auf unsere Pokebattler-IDs abgebildet, damit der Kalender auf die
Konter-Auswertung verlinken kann.
"""
import datetime
import json
import os
import re
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DATA = os.path.join(ROOT, "data")

FEEDS = {
    "events": "https://raw.githubusercontent.com/bigfoott/ScrapedDuck/data/events.json",
    "raids": "https://raw.githubusercontent.com/bigfoott/ScrapedDuck/data/raids.json",
}

# Wie lange der Kalender nach vorne und hinten reicht.
DAYS_BACK = 7
DAYS_AHEAD = 45

REGIONS = ("ALOLAN", "GALARIAN", "HISUIAN", "PALDEAN")

# Die Raid-Rotation steckt in den Event-Namen: "Mega Venusaur in Mega Raids",
# "Xurkitree, Pheromosa, and Buzzwole in 5-star Raid Battles". Daraus laesst sich der
# ganze Kalender fuellen, nicht nur die Woche, die in events_extra.json steht.
RAID_SUFFIXES = [
    (" in Mega Raids", "mega"),
    (" in 5-star Raid Battles", "t5"),
    (" in 5-Star Raid Battles", "t5"),
    (" in Shadow Raids", "shadow"),
    (" in Elite Raids", "t5"),
]
SLOTS = ("mega", "t5", "shadow")


def split_names(text):
    """'A, B, and C' -> ['A', 'B', 'C'] - Klammern wie '(Altered Forme)' bleiben heil."""
    text = re.sub(r",?\s+and\s+", ", ", text)
    return [part.strip() for part in text.split(", ") if part.strip()]


def parse_raid_event(name):
    """Liefert (slot, [Namen]) oder (None, []), wenn der Name keine Rotation beschreibt."""
    for suffix, slot in RAID_SUFFIXES:
        if name.endswith(suffix):
            return slot, split_names(name[: -len(suffix)])
    return None, []


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "counter-stats/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.load(resp)


def norm(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def make_matcher():
    """Bildet Anzeigenamen von Leek Duck auf Pokebattler-IDs ab."""
    ids = [p["pokemonId"] for p in json.load(open(os.path.join(DATA, "pokemon.json")))["pokemon"]]
    index = {}
    for pid in ids:
        index.setdefault(norm(pid), pid)

    def match(name):
        n = name.strip()
        shadow = n.startswith("Shadow ")
        if shadow:
            n = n[len("Shadow "):]
        armored = n.startswith("Armored ")
        if armored:
            n = n[len("Armored "):]
        mega = n.startswith("Mega ")
        if mega:
            n = n[len("Mega "):]
        m = re.match(r"^(.*?)\s*\((.*)\)$", n)
        form = ""
        if m:
            n, form = m.group(1), m.group(2)

        base = norm(n)
        cands = []
        if armored:
            cands += [base + "AFORM", base + "ARMORED"]
        # Regionalformen stehen bei Leek Duck vorne, in der ID hinten.
        for region in REGIONS:
            if base.startswith(region):
                rest = base[len(region):]
                cands += [rest + region + "FORM", rest + region]
        if mega:
            # "Mega X Raichu" und "Mega Raichu X" meinen dasselbe.
            mx = re.match(r"^(X|Y)(.+)$", base)
            if mx:
                cands.append(mx.group(2) + "MEGA" + mx.group(1))
            cands += [base + "MEGA", base + "MEGAX", base + "MEGAY"]
        if form:
            # Leek Duck schreibt "Altered Forme", die ID heisst GIRATINA_ALTERED_FORM.
            f = norm(form)
            if f.endswith("FORME"):
                f = f[:-1]
            cands += [base + f, base + f + "FORM"]
        cands.append(base)

        for c in cands:
            if c not in index:
                continue
            pid = index[c]
            if not shadow:
                return pid
            # Krypto-Formen gibt es nicht zu jeder Unterform: Pokebattler kennt
            # GIRATINA_SHADOW_FORM, aber kein GIRATINA_ALTERED_FORM_SHADOW_FORM.
            for guess in (pid + "_SHADOW_FORM",
                          re.sub(r"_[A-Z]+_FORM$", "", pid) + "_SHADOW_FORM"):
                if norm(guess) in index:
                    return index[norm(guess)]
            return pid
        return None

    return match


def day_range(events):
    today = datetime.date.today()
    return (today - datetime.timedelta(days=DAYS_BACK),
            today + datetime.timedelta(days=DAYS_AHEAD))


def as_date(stamp):
    return stamp[:10] if stamp else None


def main():
    match = make_matcher()
    raw_events = fetch(FEEDS["events"])
    raw_raids = fetch(FEEDS["raids"])

    extra_path = os.path.join(DATA, "events_extra.json")
    extra = json.load(open(extra_path)) if os.path.exists(extra_path) else {}

    first, last = day_range(raw_events)
    days = {}
    d = first
    while d <= last:
        days[d.isoformat()] = {"events": [], "mega": [], "t5": [], "shadow": []}
        d += datetime.timedelta(days=1)

    events = []
    for e in raw_events:
        start, end = as_date(e.get("start")), as_date(e.get("end")) or as_date(e.get("start"))
        if not start:
            continue
        item = {
            "id": e.get("eventID"),
            "name": e.get("name"),
            "type": e.get("eventType"),
            "heading": e.get("heading"),
            "link": e.get("link"),
            "start": e.get("start"),
            "end": e.get("end"),
        }
        events.append(item)
        slot, names = parse_raid_event(item["name"] or "")
        found = [match(n) for n in names] if slot else []
        d = datetime.date.fromisoformat(start)
        stop = datetime.date.fromisoformat(end)
        while d <= stop:
            key = d.isoformat()
            if key in days:
                days[key]["events"].append(item["id"])
                for pid in found:
                    if pid:
                        days[key][slot].append(pid)
            d += datetime.timedelta(days=1)
        if slot and not all(found):
            print("nicht zugeordnet in %r: %s"
                  % (item["name"], ", ".join(n for n, f in zip(names, found) if not f)))

    # Aktuelle Raid-Bosse nach Stufe.
    raids = {}
    for r in raw_raids:
        raids.setdefault(r["tier"], []).append({
            "name": r["name"],
            "id": match(r["name"]),
            "shiny": r.get("canBeShiny", False),
            "types": [t["name"] for t in r.get("types", [])],
        })

    # Tagesgenaue Nachtraege.
    for key, add in (extra.get("days") or {}).items():
        if key in days:
            for slot in SLOTS:
                days[key][slot] += add.get(slot, [])
    for span, add in (extra.get("ranges") or {}).items():
        start, stop = span.split("/")
        d = datetime.date.fromisoformat(start)
        stop = datetime.date.fromisoformat(stop)
        while d <= stop:
            key = d.isoformat()
            if key in days:
                for slot in SLOTS:
                    days[key][slot] += add.get(slot, [])
            d += datetime.timedelta(days=1)

    out = {
        "fetched": datetime.date.today().isoformat(),
        "events": sorted(events, key=lambda x: x["start"] or ""),
        "raids": raids,
        "days": days,
    }
    with open(os.path.join(DATA, "events.json"), "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    # Tippfehler in events_extra.json wuerden sonst als leerer Kalendereintrag durchgehen.
    known = {x["pokemonId"] for x in json.load(
        open(os.path.join(DATA, "pokemon.json")))["pokemon"]}
    unknown = sorted({pid for day in days.values() for slot in SLOTS
                      for pid in day[slot] if pid not in known})
    if unknown:
        print("events_extra.json: unbekannte IDs: %s" % ", ".join(unknown))

    unmatched = [b["name"] for v in raids.values() for b in v if not b["id"]]
    filled = sum(1 for day in days.values() if any(day[s] for s in SLOTS))
    print("Events: %d, Raid-Bosse: %d, Tage: %d (%d mit Bossen)"
          % (len(events), sum(len(v) for v in raids.values()), len(days), filled))
    for tier, bosses in raids.items():
        print("  %-16s %s" % (tier, ", ".join(b["name"] for b in bosses)))
    if unmatched:
        print("ohne Zuordnung: %s" % ", ".join(unmatched))


if __name__ == "__main__":
    main()
