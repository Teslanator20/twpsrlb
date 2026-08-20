# Pokémon GO – Counter-Rangliste der Raidbosse

Auswertung der **fünf schnellsten Konter aller legendären, mysteriösen und Ultrabestien-
Raidbosse sowie aller Mega- und Proto-Raids**, mit Angreifern auf **Level 50**, auf Basis der
[Pokebattler](https://www.pokebattler.com/)-Simulations-API – einmal **mit Team-Power und
bestem Freund**, einmal **ohne beides**. Mega-Entwicklungen stehen in einer eigenen dritten
Spalte und zählen dort nur, wenn sie sich auch gegen die normalen Konter durchsetzen.

Ergebnis ist eine statische Website (`index.html`, keine Abhängigkeiten, kein Build-Tooling)
mit drei Ranglisten-Abschnitten – über alle fünf Platzierungen, nur über Platz 1 und 2, und nur
über Platz 1 – einer kombinierten Bestenliste über den vollen Pool, einer Übersicht der besten Angreifer je
Attacken-Typ und einer durchsuchbaren Detailansicht pro Boss.

## Was drin steht

* **252 Raidbosse**, jeder in seiner eigenen Raid-Stufe:
  * **150 Stufe-5-Bosse** (legendär und mysteriös), inklusive aller Arceus- und Silvally-Formen,
    Giratina Urform, Necrozma Morgenschwingen, Zacian König des Schwertes, Deoxys in allen Formen
  * **78 Mega-Raids**: von Mega-Bisaflor bis Mega-Knakrack, auch die nicht-legendären
  * **12 legendäre Mega- und Proto-Raids** plus **1 Mega-Enhanced**
  * **11 Ultrabestien**: Nihilego, Pheromosa, Kartana, Guzzlord und die anderen
  * **1 Elite-Raid**: Regieleki

  Enthalten sind auch Bosse aus Pokebattlers Vorschau-Listen. Die führen einerseits noch
  unveröffentlichte Bosse, andererseits solche, die längst im Spiel waren, ohne dass die
  Liste nachgezogen wurde – Lunala zum Beispiel.
* Pro Boss die **fünf besten Konter je Konfiguration und Pool** – also vier Listen pro Boss:
  mit/ohne Boni, jeweils ohne Megas und nur Megas. Jedes Pokémon ist **ein Eintrag**; darunter
  stehen seine **drei schnellsten Attackensets mit jeweils eigener Zeit**.
* **Drei Ranglisten-Abschnitte mit identischem Aufbau**, je drei Spalten, nach Zähltiefe:
  alle fünf Platzierungen, nur Platz 1 und 2, nur Platz 1. Sie zeigen, wie oft ein Pokémon
  gelistet ist, wie oft es Platz 1 belegt und wie stark sich sein Rang zwischen den beiden
  Konfigurationen verschiebt. Die Mega-Spalte zeigt beide Zählungen nebeneinander.
* Ein **Schalter für Krypto-Pokémon**, standardmäßig aus: Krypto-Formen sind aus allen Spalten
  genommen und lassen sich per Klick einblenden. Beide Varianten sind vorberechnet, das
  Umschalten läuft ohne Nachladen. Sobald der Schalter aus dem Blick scrollt, erscheint oben
  eine **mitlaufende Leiste** mit demselben Schalter und der aktiven Auswahl.
* Eine **kombinierte Bestenliste** ganz unten: pro Boss zählt nur, wer tatsächlich vorn liegt –
  Mega, Krypto oder normal in einer Reihe. Führt ein Mega, kommt zusätzlich der beste Nicht-Mega
  dazu. Diese Liste nutzt immer den vollen Pool und ignoriert den Krypto-Schalter; beim Aufklappen
  steht, wie oft ein Pokémon selbst vorn lag und wie oft es nur als bester Nicht-Mega dazukam.
* **Die besten Angreifer je Attacken-Typ**: 18 Karten, gruppiert nach dem Typ der Lade-Attacke,
  mit der ein Pokémon seine Platzierung geholt hat – nicht nach seinem eigenen Typ. Mega-Mewtu Y
  steht dadurch bei Eis, Elektro, Psycho und Geist. Gezählt sind alle Top-5-Platzierungen beider
  Konfigurationen und beider Pools; der Krypto-Schalter gilt hier mit.
* Ein Klick auf ein Pokémon in einer Rangliste öffnet darunter eine **Attackenset-Auswertung**:
  mit welchem Set es seine Platzierungen geholt hat, in beiden Konfigurationen, mit Anzahl,
  Anteil und den zugehörigen Bossen. Bei Mega-Mewtu Y sind das sechs verschiedene Lade-Attacken.

## Die drei Spalten

| Spalte | Team-Power | Freundschaft | Pool | API-Parameter |
|---|---|---|---|---|
| **Mit Boni** | ja (Gruppengröße 2) | bester Freund | ohne Megas | `numParty=2`, `friendLevel=FRIENDSHIP_LEVEL_4` |
| **Ohne Boni** | nein | keine | ohne Megas | `numParty=1`, `friendLevel=FRIENDSHIP_LEVEL_0` |
| **Megas im Gesamtvergleich** | beide Konfigurationen | | nur Megas, gemessen an allen | – |

Sonst identisch: jeder Boss in seiner eigenen Raid-Stufe, Angreifer auf **Level 50**, Strategie
`CINEMATIC_ATTACK_WHEN_POSSIBLE`, Ausweichen nach Reaktionszeit, kein Wetterbonus,
zufälliges Boss-Attackenset, sortiert nach Time to win.

## Die Vergleichsgröße: Time to win

Sortiert und gewertet wird nach `TIME` – Pokebattlers „Time to win assuming infinite number
of Pokemon". Der Gedanke dahinter: mit unbegrenzt vielen Exemplaren schafft jeder Angreifer
jedes Boss-Attackenset, unterschiedlich ist nur die Dauer. Das macht die Zahlen über Bosse
hinweg vergleichbar, wo der Estimator (geschätzte Trainer-Anzahl) bei 1,0 abschneidet. Der
Estimator läuft als Zusatzinfo mit.

Werte **unter 300 s** liegen im Raid-Zeitlimit – dort wird ein einzelner Trainer rechtzeitig
fertig. Nihilego solo ist mit 297,1 s (Proto-Groudon) genau so ein Grenzfall.

## Erfassung

Pokebattler liefert je Abfrage die 30 besten Konter, jeder mit 6 bis 10 durchsimulierten
Attackensets. `scrape.py` speichert die 30 Konter mit ihren jeweils **drei schnellsten** Sets,
`build.py` filtert daraus die Top 5 je Pool – und zwar zweimal: einmal ohne Krypto-Formen
(`noShadow`, die Standardansicht) und einmal mit (`withShadow`). Aus denselben Trefferlisten
entstehen alle drei Zähltiefen (`top5`, `top2`, `top1`), die strengeren sind also immer
Teilmengen der lockeren.

Gezählt wird immer **pro Pokémon**, nicht pro Attackenset: Mega-Mewtu Y mit Spukball und
Mega-Mewtu Y mit Eisstrahl sind ein Eintrag in der Rangliste. Welches Set wie oft zum Zug
kam, zeigt die Klick-Box.

Die Platzierung wird je Spalte unterschiedlich gemessen, und das ist Absicht. Die ersten zwei
Spalten beantworten „was nehme ich ohne Mega“ und zählen deshalb innerhalb ihres Pools. Die
Mega-Spalte beantwortet „lohnt sich die Mega-Energie“ – dort zählt die Position im
**Gesamtvergleich**: `merge()` legt die Spitzen beider Pools zusammen, und ein Mega bekommt
seine Platzierung nur, wenn es auch die Nicht-Megas schlägt. Gegen Rayquaza etwa liegt
Mega-Mewtu Y mit Eisstrahl hinter beiden Kyurem-Formen und zählt dort nicht als Platz 1.

Als Mega zählen alle IDs mit `_MEGA` sowie Proto-Groudon und Proto-Kyogre (`_PRIMAL`) –
in Pokémon GO dieselbe Mechanik. Als Krypto zählen alle IDs mit `_SHADOW_FORM`. Krypto-Megas
gibt es nicht, der Krypto-Schalter verändert die Mega-Spalte aber trotzdem: eingeblendete
Krypto-Formen konkurrieren im Gesamtvergleich mit und drängen Megas aus den Platzierungen.

## Aufbau

```
index.html          fertige Website (Daten sind eingebettet, läuft auch per file://)
data.json           dieselben Daten als reines JSON
data/counters.json  Rohergebnis der API-Abfrage (30 Konter je Boss und Konfiguration)
data/bosses.json    Liste der ausgewerteten Bosse mit ihrer Raid-Stufe
data/pokemon.json   abgespeckter Pokedex von Pokebattler (Typen, Nummern, Seltenheit)
data/move_types.json     Attacke -> Typ, für die Gruppierung nach Lade-Attacke
data/de_constants.json   deutsche Pokémon- und Attackennamen von Pokebattler
tools/bosses.py     stellt die Boss-Liste samt Raid-Stufe zusammen und aktualisiert pokemon.json
tools/scrape.py     holt die Counter von der Pokebattler-API
tools/build.py      trennt Megas und Krypto ab, rechnet Ranglisten aus und schreibt data.json
tools/render.py     baut index.html aus template.html + data.json
tools/template.html Vorlage der Website (Platzhalter __DATA__)
```

## Neu erzeugen

```bash
python3 tools/bosses.py    # Boss-Liste neu aufbauen (fragt die Raid-Listen bei Pokebattler ab)
python3 tools/scrape.py    # nur nötig, wenn die Daten aktualisiert werden sollen
python3 tools/render.py    # ruft build.py mit auf und schreibt data.json + index.html
```

Level-50-Abfragen liegen bei Pokebattler selten im Cache und laufen beim ersten Mal
reproduzierbar in dessen 30-Sekunden-Timeout. Der Server rechnet danach aber weiter, und ein
Abbruch nach 3 Sekunden genügt, um die Berechnung anzustoßen. Deshalb läuft die Erfassung in
zwei Phasen:

```bash
WARMUP=1 python3 tools/scrape.py   # stößt alles an, bricht nach 3 s ab (~25 min)
python3 tools/scrape.py            # sammelt die Ergebnisse ein
RETRY_FAILED=1 python3 tools/scrape.py   # für Nachzügler
```

So kamen alle 504 Abfragen ohne einen einzigen Fehlschlag herein. Ohne Vorwärmen scheitern
rund 90 % der Level-50-Abfragen dauerhaft. `scrape.py` schreibt fortlaufend in
`data/counters.json` und überspringt vorhandene Einträge; Fehlschläge landen als `null` und
werden übersprungen, bis `RETRY_FAILED=1` sie erneut aufgreift.

## Deployment

Die Seite ist statisches HTML ohne Build-Schritt – `index.html` liegt im Repo-Wurzelverzeichnis.
Damit läuft sie auf jedem Static-Host ohne Konfiguration.

**Vercel, per GitHub-Import:** auf [vercel.com/new](https://vercel.com/new) das Repo auswählen,
Framework Preset `Other`, Build Command und Output Directory leer lassen, deployen. Jeder
weitere Push auf `main` deployt automatisch.

**Vercel, per CLI:**

```bash
npx vercel deploy --prod   # im Repo-Wurzelverzeichnis, fragt beim ersten Mal nach dem Login
```

**GitHub Pages:** im Repo unter Settings → Pages als Quelle `main` / `/ (root)` wählen.

## Einschränkungen

* Der Angreifer-Pool ist Pokebattlers Standard und enthält auch noch nicht veröffentlichte
  Formen; er bildet also ab, was theoretisch am stärksten ist, nicht was jeder im Beutel hat.
  Krypto-Formen sind deshalb standardmäßig ausgeblendet.
* Jede Form zählt einzeln – Schwarzes Kyurem und Kyurem sind getrennte Einträge.
* Es sind nur Bosse berücksichtigt, die tatsächlich schon in Raids aufgetreten sind
  (aktuelle + Legacy-Listen). Angekündigte, aber unveröffentlichte Mega-Bosse wie Mega-Diancie,
  Mega-Darkrai, Mega-Heatran, Mega-Zeraora und Mega-Zygarde fehlen deshalb.
* Krypto-Raidbosse sind nicht dabei – die gehören in eine eigene Auswertung.
* Zwei Lade-Attacken fehlen im deutschen Namensverzeichnis von Pokebattler und stehen deshalb
  englisch da: „Mind Blown“ (Kopplosio) und „Secret Sword“ (Keldeo).
* Die Top 5 je Pool stammen aus den 30 gelieferten Kontern. Das reicht fast immer; wo nach
  dem Filtern weniger als 5 übrig bleiben, ist die Liste entsprechend kürzer.
* Die Boss-Liste lädt in Blöcken von 30 Karten – 252 Bosse komplett im DOM machen die Seite träge.
* Team-Power ist mit Gruppengröße 2 simuliert. `numParty=3` und `numParty=4` beantwortet die
  Pokebattler-API nicht innerhalb ihres 30-Sekunden-Timeouts.
* Der Datensatz ist vollständig: 504 von 504 Abfragen, keine Lücken.

Daten von Pokebattler. Pokémon ist eine Marke von Nintendo/Creatures Inc./GAME FREAK inc.
Dieses Projekt steht in keiner Verbindung zu Niantic oder Nintendo.
