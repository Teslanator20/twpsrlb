#!/usr/bin/env python3
"""Erzeugt die fertige index.html: Template + eingebettete data.json."""
import json
import os

import build

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("OUT_DIR", os.path.dirname(HERE))


def main():
    data = build.main()
    template = open(os.path.join(HERE, "template.html"), encoding="utf-8").read()
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    # </script> im JSON wuerde das Script vorzeitig schliessen
    payload = payload.replace("</", "<\\/")
    html = template.replace("__DATA__", payload)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(html)
    print("geschrieben: %s (%.1f KB)" % (path, os.path.getsize(path) / 1024))


if __name__ == "__main__":
    main()
