# Dissertation Website

A static GitHub Pages website generated from `TOWARD DESIGN-TO-FABRICATION CONTINUUMV5.docx`.

## Contents

- `index.html` — website entry point
- `content/` — one Markdown file per chapter, interlude, front-matter item, and appendix
- `content/html/` — pre-rendered HTML fragments used by the website
- `figure/` — all figures extracted from the DOCX
- `data/references.json` — citation callout and bibliography lookup data
- `data/navigation.json` — document order and simplified table of contents
- `assets/style.css` — fonts, colors, dimensions, corners, and animation settings
- `MARKDOWN-EDITION.md` — direct links to the plain Markdown edition

## Update from a later DOCX

The script used for this conversion is included at `tools/build_site.py`. Update its `SRC` path and run it in an environment with Python, `python-docx`, Beautiful Soup, and Pandoc installed.
