# CLAUDE.md

Auswertung der besten Raid-Konter in Pokémon GO auf Basis der Pokebattler-Simulations-API.
Ergebnis ist eine einzelne, in sich geschlossene `index.html` ohne Build-Tooling und ohne
Abhängigkeiten – die Daten stecken als JSON im HTML.

Fachliche Beschreibung steht in `README.md`. Diese Datei sammelt, was beim Weiterarbeiten
Zeit spart.

## Pipeline

```bash
python3 tools/bosses.py    # Boss-Liste + Pokedex + Attacken-Typen von Pokebattler holen
python3 tools/scrape.py    # Counter je Boss holen (siehe Vorwärmen)
python3 tools/render.py    # ruft build.py auf, schreibt data.json und index.html
```

`render.py` importiert `build.py` – nie einzeln laufen lassen, wenn beide Ausgaben gebraucht
werden. Beide respektieren `OUT_DIR`, damit man ohne Risiko in ein Vorschau-Verzeichnis
rendern kann:

```bash
OUT_DIR=/tmp/preview python3 tools/render.py
```

## Vorwärmen: der wichtigste Punkt bei scrape.py

Angreifer stehen auf **Level 50**. Solche Abfragen liegen bei Pokebattler kaum im Cache und
laufen beim ersten Mal reproduzierbar in dessen 30-Sekunden-Gateway-Timeout. Der Server
rechnet danach aber weiter – und **ein Abbruch nach 3 Sekunden genügt, um das anzustoßen.**

```bash
WARMUP=1 python3 tools/scrape.py   # stößt alles an, bricht nach 3 s ab (~25 min für 500 Abfragen)
python3 tools/scrape.py            # sammelt ein
RETRY_FAILED=1 python3 tools/scrape.py   # Nachzügler
```

Ohne Vorwärmen scheitern rund 90 % der Level-50-Abfragen dauerhaft, auch mit langen
Retry-Ketten. Mit Vorwärmen kamen alle 504 Abfragen ohne einen Fehlschlag herein.

Weitere Beobachtungen zur API:

* Die **`team`-Konfiguration ist der teure Teil.** Mit `sort=TIME` braucht sie 8–14 s, mit
  `sort=ESTIMATOR` nur 0,5 s. Wer die Sortierung ändert, ändert damit auch die Laufzeit.
* Bei zu vielen parallelen Abfragen kommt `429`. `fetch()` wartet dann 60 s. Sequenziell
  bleiben.
* Fehlschläge landen als `null` in `data/counters.json` und werden bei normalen Läufen
  übersprungen, damit ein Neustart nicht in dieselben Timeouts rennt.
* `ATTEMPTS=1` für schnelles Scheitern, `ATTACKER_LEVEL` steht oben in `scrape.py`.

## Vergleichsgröße

**Time to win in Sekunden**, kleiner ist besser – Pokebattlers „Time to win assuming infinite
number of Pokemon". Der Estimator (geschätzte Trainer-Anzahl) läuft nur als Zusatzfeld mit.
Grund: mit unbegrenzt vielen Pokémon schafft jeder Angreifer jedes Boss-Attackenset,
unterschiedlich ist nur die Dauer – das macht Werte über Bosse hinweg vergleichbar, wo der
Estimator bei 1,0 abschneidet.

**300 s ist das Raid-Zeitlimit.** Darunter wird ein einzelner Trainer rechtzeitig fertig; die
Seite hebt solche Werte hervor (`.s-est.ok`).

## Semantik, die man leicht falsch macht

* **Ein Pokémon = ein Eintrag.** Gezählt wird pro Pokémon, nicht pro Attackenset. Welches Set
  wie oft zum Zug kam, zeigt die Aufklapp-Box.
* **Die Mega-Spalte zählt im Gesamtvergleich**, die beiden anderen pool-intern. Absicht: die
  ersten zwei Spalten beantworten „was nehme ich ohne Mega", die Mega-Spalte „lohnt sich die
  Mega-Energie". Ein Mega bekommt dort seine Platzierung nur, wenn es auch die Nicht-Megas
  schlägt (`merge()` in `build.py`).
* **Drei Zähltiefen** (`top5`, `top2`, `top1`) entstehen aus denselben Trefferlisten, sind also
  Teilmengen voneinander.
* **Zwei Krypto-Varianten** (`noShadow`, `withShadow`) sind beide vorberechnet; der Schalter
  wechselt nur. `noShadow` ist die Standardansicht.
* **Die kombinierte Bestenliste ignoriert den Krypto-Schalter** und nutzt immer den vollen
  Pool – sie beantwortet „was ist objektiv das Beste".
* **Der Typ eines Angreifers richtet sich nach seiner Lade-Attacke**, nicht nach seinem eigenen
  Typ. Mega-Mewtu Y steht deshalb bei Eis, Elektro, Psycho und Geist.
* Als **Mega** zählen IDs mit `_MEGA` und Protoformen (`_PRIMAL`), als **Krypto** IDs mit
  `_SHADOW_FORM`.

## Konventionen

* Oberfläche und Code-Kommentare auf **Deutsch**.
* `tools/template.html` ist die Quelle der Website; `index.html` ist generiert – **nie direkt
  editieren.** Platzhalter `__DATA__` wird von `render.py` ersetzt.
* Pokémon- und Attackennamen kommen aus `data/de_constants.json` (Pokebattlers i18n). Die
  Datei nutzt `$t(constants:…)`-Referenzen, `resolve()` in `build.py` löst die rekursiv auf und
  komponiert bei Lücken (`SHADOW_FORM` + Basisname). Zwei Attacken fehlen dort und stehen
  englisch da: „Mind Blown" und „Secret Sword".
* **Theme-Tokens:** Farben nur über CSS-Variablen, jede Variable im blanken `:root` definieren
  und in den beiden Dark-Blöcken überschreiben. Eine Farbe, die nur in einem `@media`- oder
  `[data-theme]`-Block steht, fehlt im ungesetzten Zustand.
* **Achtung Klassennamen-Kollisionen.** Es gab schon einen Fall: `.n` der Rangliste steht auf
  `display:flex` und hat die gleichnamige Klasse in den Attackensets zerschossen. Bei neuen
  Bausteinen eigene Präfixe verwenden (`.s-rank`, `.dr-…`, `.who3`).
* Die **Boss-Liste lädt in Blöcken von 30** (`state.bossLimit`). 252 Bosse komplett im DOM
  kosten 71.000 Knoten und zwei Sekunden Ladezeit. Suche und Filter greifen auf alle Bosse zu,
  nur die Darstellung ist begrenzt.

## Prüfen

Chromium und Playwright liegen im Container bereit
(`/opt/node22/lib/node_modules/playwright`, `executablePath: '/opt/pw-browsers/chromium'`).
Vor dem Deployen jeweils geprüft: keine Konsolenfehler, `scrollWidth == innerWidth` bei 1440
und 390 Pixeln, hell und dunkel, und die interaktiven Teile (Krypto-Schalter, Aufklapp-Boxen,
Typ-Auswahl, Suche, Nachladen).

## Deployment

Statisches HTML, kein Build-Schritt. Auf Vercel liegt das Projekt `pokemongocounters`
(Framework `Other`, kein Build Command). `.vercelignore` hält `data/` und `tools/` zurück –
ohne das gehen 8 MB Rohdaten mit hoch und der Upload bricht ab.

**Der Commit-Autor muss zu einem Git-Account passen.** Vercel setzt Deployments sonst auf
`BLOCKED`, ohne den Build zu starten – die Fehlermeldung nennt nur die E-Mail. Im Repo ist
`user.email` deshalb lokal gesetzt.
