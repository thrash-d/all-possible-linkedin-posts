#!/usr/bin/env python3
"""Bundle the page and dictionary into one double-clickable file.

Reads linkedin-posts.html (the editable source, which fetches lexicon.json)
and lexicon.json, and writes linkedin-posts-standalone.html with the dictionary
embedded and the fetch replaced by an in-page read.

Also writes index.html, the source wrapped in a full HTML document with the
fetch kept. That's the GitHub Pages copy: it loads lexicon.json separately,
which Pages serves gzipped, instead of shipping the whole dictionary inline.

Run from anywhere:
    python build/make_standalone.py
"""

import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "linkedin-posts.html"
LEX = ROOT / "lexicon.json"
OUT = ROOT / "linkedin-posts-standalone.html"
WEB = ROOT / "index.html"

SKELETON = (
    '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
    '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
)


def main():
    src = SRC.read_text(encoding="utf-8")
    lex = LEX.read_text(encoding="utf-8")

    # The source is a fragment with no <html>, <head>, or <body>.
    head, _, rest = src.partition("</style>")
    page = SKELETON + head + "</style>\n</head>\n<body>\n" + rest + "\n</body>\n</html>\n"

    WEB.write_text(page, encoding="utf-8")
    print(f"Wrote {WEB.name} ({len(page) / 1e3:.0f} KB)")

    # Escape so the JSON can't terminate the <script> block or break line parsing.
    safe = lex.replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    data_block = '<script id="lexicon-data" type="application/json">' + safe + "</script>\n<script>"
    page = page.replace('<script>\n(() => {\n  "use strict";',
                        data_block + '\n(() => {\n  "use strict";', 1)

    # Swap the fetch loader for an embedded-JSON read.
    loader = re.search(r"  function fail\(msg\).*?\}\)\(\);", page, re.S).group(0)
    embedded = (
        '  function fail(msg) { $("count").textContent = ""; $("loading").textContent = msg; }\n'
        "  try {\n"
        '    LEX = JSON.parse(document.getElementById("lexicon-data").textContent);\n'
        "    start();\n"
        '  } catch (e) { fail("Couldn\'t build the feed: " + e.message); }\n'
        "})();"
    )
    page = page.replace(loader, embedded, 1)

    OUT.write_text(page, encoding="utf-8")
    print(f"Wrote {OUT.name} ({len(page) / 1e6:.2f} MB)")


if __name__ == "__main__":
    main()
