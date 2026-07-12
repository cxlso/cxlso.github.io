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

## Publish with GitHub Pages

1. Copy the contents of this folder into a GitHub repository.
2. Open **Settings → Pages**.
3. Select **Deploy from a branch**.
4. Select the `main` branch and the repository root.
5. Save.

All paths are relative, so the site can be published at a user-domain root or inside a project subdirectory.

## Change the visual style

Edit the variables at the beginning of `assets/style.css`:

```css
:root {
  --font-ui: "Funnel Display", Arial, sans-serif;
  --font-body: "Funnel Display", Arial, sans-serif;
  --background: #ffffff;
  --foreground: #000000;
  --panel: rgba(0, 0, 0, 0.86);
  --corner: 8px;
  --reading-width: 760px;
  --body-size: 16px;
}
```

The initial style follows the visual language of the literature graph: Funnel Display Light, white background, black controls, floating black citation callouts, short interface transitions, and a long vertical rail aligned beside the reading column.

## Update from a later DOCX

The script used for this conversion is included at `tools/build_site.py`. Update its `SRC` path and run it in an environment with Python, `python-docx`, Beautiful Soup, and Pandoc installed.
