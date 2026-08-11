# Pokémon GO – Counter-Rangliste der legendären Raidbosse

Auswertung der **Top-5-Konter aller legendären und mysteriösen Stufe-5-Raidbosse**
auf Basis der [Pokebattler](https://www.pokebattler.com/)-Simulations-API – einmal
**mit Team-Power und bestem Freund**, einmal **ohne beides**.

Ergebnis ist eine statische Website (`index.html`, keine Abhängigkeiten, kein Build-Tooling)
mit zwei Ranglisten nebeneinander plus einer durchsuchbaren Detailansicht pro Boss.

## Was drin steht

* **69 Raidbosse** – alle legendären und mysteriösen Stufe-5-Bosse, die Pokebattler kennt
  (aktuelle + Legacy-Raids), inklusive Formen wie Giratina Urform, Necrozma Morgenschwingen,
  Zacian König des Schwertes oder Deoxys in allen vier Formen.
* Pro Boss und Konfiguration die **fünf besten Konter** mit Attackenset und Estimator.
* Zwei **Häufigkeitsranglisten**: wie oft ein Pokémon in den Top 5 landet, wie oft es Platz 1 belegt
  und wie stark sich sein Rang zwischen den beiden Konfigurationen verschiebt.

## Die zwei Konfigurationen

| | Team-Power | Freundschaft | API-Parameter |
|---|---|---|---|
| **Mit Boni** | ja (Gruppengröße 2) | bester Freund | `numParty=2`, `friendLevel=FRIENDSHIP_LEVEL_4` |
| **Ohne Boni** | nein | keine | `numParty=1`, `friendLevel=FRIENDSHIP_LEVEL_0` |

Sonst identisch: Stufe-5-Raid, Angreifer auf Level 40, Strategie
`CINEMATIC_ATTACK_WHEN_POSSIBLE`, Ausweichen nach Reaktionszeit, kein Wetterbonus,
zufälliges Boss-Attackenset, sortiert nach Estimator.

## Aufbau

```
index.html          fertige Website (Daten sind eingebettet, läuft auch per file://)
data.json           dieselben Daten als reines JSON
data/counters.json  Rohergebnis der API-Abfrage (Top 5 je Boss und Konfiguration)
data/legendary_ids.json  Liste der ausgewerteten Bosse
data/pokemon.json   abgespeckter Pokedex von Pokebattler (Typen, Nummern, Seltenheit)
data/de_constants.json   deutsche Pokémon- und Attackennamen von Pokebattler
tools/scrape.py     holt die Counter von der Pokebattler-API
tools/build.py      rechnet Ranglisten aus und schreibt data.json
tools/render.py     baut index.html aus template.html + data.json
tools/template.html Vorlage der Website (Platzhalter __DATA__)
```

## Neu erzeugen

```bash
python3 tools/scrape.py    # nur nötig, wenn die Daten aktualisiert werden sollen
python3 tools/render.py    # ruft build.py mit auf und schreibt data.json + index.html
```

`scrape.py` schreibt fortlaufend in `data/counters.json` und überspringt bereits vorhandene
Einträge – ein abgebrochener Lauf lässt sich einfach neu starten.

## Einschränkungen

* Der Angreifer-Pool ist Pokebattlers Standard. Er enthält auch Mega-, Krypto- und noch nicht
  veröffentlichte Formen; er bildet also ab, was theoretisch am stärksten ist, nicht was jeder
  im Beutel hat.
* Jede Form zählt einzeln – Mega-Mewtu Y und Mewtu sind getrennte Einträge.
* Team-Power ist mit Gruppengröße 2 simuliert. `numParty=3` und `numParty=4` beantwortet die
  Pokebattler-API nicht innerhalb ihres 30-Sekunden-Timeouts.
* Für **Rüstungs-Mewtu** und **Deoxys (Normalform)** liefert die API in der Team-Power-Variante
  dauerhaft eine Zeitüberschreitung. Diese beiden Felder bleiben leer und sind auf der Seite
  als solche gekennzeichnet.

Daten von Pokebattler. Pokémon ist eine Marke von Nintendo/Creatures Inc./GAME FREAK inc.
Dieses Projekt steht in keiner Verbindung zu Niantic oder Nintendo.
