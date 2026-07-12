from __future__ import annotations

import html
import json
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup, NavigableString, Tag

SRC = Path('/mnt/data/TOWARD DESIGN-TO-FABRICATION CONTINUUMV5.docx')
WORK = Path('/mnt/data/dissertation_site_work')
OUT = Path('/mnt/data/dissertation-website')
FULL_MD = WORK / 'full.md'
MEDIA_DIR = WORK / 'media' / 'media'

TITLE = 'Toward Design-to-Fabrication Continuum for Open-Source Computational Robotic Ecologies in the Post-Anthropogenic Era'
AUTHOR = 'Celso Urroz'
INSTITUTION = 'Florida Atlantic University'
DEGREE = 'Doctor of Philosophy'
DATE = 'August 2026'


def run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)


def slugify(value: str) -> str:
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = value.lower().replace('&', ' and ')
    value = re.sub(r'[^a-z0-9]+', '-', value).strip('-')
    return value or 'item'


def clean_inline_md(text: str) -> str:
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def extract_between(text: str, start: str, end: str | None) -> str:
    a = text.index(start)
    b = text.index(end, a + len(start)) if end else len(text)
    return text[a:b].strip() + '\n'


def strip_first_heading(md: str) -> str:
    lines = md.splitlines()
    if lines and lines[0].startswith('#'):
        lines = lines[1:]
    while lines and not lines[0].strip():
        lines.pop(0)
    return '\n'.join(lines).strip() + '\n'


def roman(n: int) -> str:
    vals = [(10, 'X'), (9, 'IX'), (5, 'V'), (4, 'IV'), (1, 'I')]
    out = ''
    for v, s in vals:
        while n >= v:
            out += s
            n -= v
    return out


def number_chapter_headings(md: str, chapter_no: int) -> tuple[str, list[dict]]:
    h2 = 0
    h3 = 0
    sections: list[dict] = []
    out: list[str] = []
    for line in md.splitlines():
        if line.startswith('### '):
            h3 += 1
            title = line[4:].strip()
            title = re.sub(r'^\d+(?:\.\d+)+\s+', '', title)
            number = f'{chapter_no}.{h2}.{h3}'
            out.append(f'### {number} {title}')
            sections.append({'number': number, 'title': title})
        elif line.startswith('## '):
            h2 += 1
            h3 = 0
            title = line[3:].strip()
            title = re.sub(r'^\d+(?:\.\d+)+\s+', '', title)
            number = f'{chapter_no}.{h2}'
            out.append(f'## {number} {title}')
            sections.append({'number': number, 'title': title})
        else:
            out.append(line)
    return '\n'.join(out).strip() + '\n', sections


def transform_interlude_headings(md: str, label: str) -> tuple[str, list[dict]]:
    lines = md.splitlines()
    out: list[str] = []
    sections: list[dict] = []
    count = 0
    i = 0
    start_re = re.compile(r'^\s*\d+\.\s+(?:\d+\.\s+)?(?:<span[^>]*></span>)?(.*)$')
    while i < len(lines):
        m = start_re.match(lines[i])
        if m:
            title_parts = [m.group(1).strip()] if m.group(1).strip() else []
            j = i + 1
            while j < len(lines) and lines[j].startswith('    ') and lines[j].strip():
                title_parts.append(lines[j].strip())
                j += 1
            title = ' '.join(title_parts).strip()
            if title:
                count += 1
                num = f'{label}.{roman(count)}'
                out.append(f'## {num} {title}')
                sections.append({'number': num, 'title': title})
            i = j
            continue
        if re.match(r'^\s*\d+\.\s*$', lines[i]):
            i += 1
            continue
        out.append(lines[i])
        i += 1
    return '\n'.join(out).strip() + '\n', sections


def split_appendices(md: str) -> list[tuple[str, str, str]]:
    body = strip_first_heading(md)
    pat = re.compile(r'^#######\s+(.+)$', re.M)
    matches = list(pat.finditer(body))
    titles = [
        ('appendix-a', 'Appendix A — Essay on Decentralized Indexing and the Scales of Civilization'),
        ('appendix-b', 'Appendix B — Open-Source Repositories and Digital Research Outputs'),
        ('appendix-c', 'Appendix C — Workflow Dependencies and Reproducibility Matrix'),
    ]
    result = []
    for idx, m in enumerate(matches):
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        slug, heading = titles[idx]
        content = body[start:end].strip()
        result.append((slug, heading, f'# {heading}\n\n{content}\n'))
    return result


def parse_bibliography(md: str) -> list[dict]:
    md = strip_first_heading(md)
    blocks = [b.strip() for b in re.split(r'\n\s*\n', md) if b.strip()]
    refs: list[dict] = []
    used: dict[str, int] = {}
    for block in blocks:
        flat = re.sub(r'\s+', ' ', block).strip().replace('\\[', '[').replace('\\]', ']')
        year_match = re.search(r'\((18|19|20)\d{2}[a-z]?\)', flat)
        if not year_match:
            continue
        year = year_match.group(0)[1:-1]
        author = flat[:year_match.start()].strip().rstrip(', ')
        after = flat[year_match.end():].lstrip(' .')
        # Publication title: first sentence after the year. Preserve question marks if present.
        # The popup uses only the publication title, not journal/publisher/URL details.
        title = re.split(r'\.\s+', after, maxsplit=1)[0].strip().rstrip('.')
        title = title.replace('\\[', '[').replace('\\]', ']')
        urls = re.findall(r'https?://[^\s)]+', flat)
        first_surname_match = re.match(r"([A-Za-zÀ-ÖØ-öø-ÿ'’\-]+)", author)
        first_surname = first_surname_match.group(1) if first_surname_match else 'reference'
        base = slugify(f'{first_surname}-{year}')
        used[base] = used.get(base, 0) + 1
        rid = base if used[base] == 1 else f'{base}-{used[base]}'
        refs.append({
            'id': rid,
            'author': author,
            'year': year,
            'title': title,
            'text': flat,
            'urls': urls,
            'display': f'{author}, {year}. {title}',
        })
    return refs


def ref_surnames(author: str) -> list[str]:
    # APA author string: surnames precede initials. Collect likely surname tokens.
    names = []
    for m in re.finditer(r'(?:^|,\s*&?\s*|;\s*)([A-Za-zÀ-ÖØ-öø-ÿ][A-Za-zÀ-ÖØ-öø-ÿ\-’\']+),\s*[A-Z]', author):
        names.append(m.group(1))
    if not names:
        m = re.match(r'([A-Za-zÀ-ÖØ-öø-ÿ\-’\']+)', author)
        if m:
            names.append(m.group(1))
    return names


def build_ref_index(refs: list[dict]) -> dict[str, list[str]]:
    idx: dict[str, list[str]] = {}
    for ref in refs:
        surnames = ref_surnames(ref['author'])
        year = ref['year'].lower()
        variants = []
        if surnames:
            variants.append(f'{surnames[0].lower()}|{year}')
            if len(surnames) >= 2:
                variants.append(f'{surnames[0].lower()}&{surnames[1].lower()}|{year}')
        for v in variants:
            idx.setdefault(v, []).append(ref['id'])
    return idx


def match_citation_part(part: str, ref_index: dict[str, list[str]]) -> str | None:
    part = clean_inline_md(part)
    ym = re.search(r'((?:18|19|20)\d{2}[a-z]?)', part)
    if not ym:
        return None
    year = ym.group(1).lower()
    before = part[:ym.start()].strip().rstrip(', ')
    before = re.sub(r'\bet\s+al\.?$', '', before, flags=re.I).strip()
    # Handle narrative fragments and multiple authors.
    surnames = re.findall(r"[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ\-’']+", before)
    if not surnames:
        return None
    keys = []
    if '&' in before or ' and ' in before:
        if len(surnames) >= 2:
            keys.append(f'{surnames[0].lower()}&{surnames[1].lower()}|{year}')
    keys.append(f'{surnames[0].lower()}|{year}')
    for key in keys:
        candidates = ref_index.get(key)
        if candidates:
            return candidates[0]
    return None


def citation_ids(citation_text: str, ref_index: dict[str, list[str]]) -> list[str]:
    inner = citation_text.strip()
    if inner.startswith('(') and inner.endswith(')'):
        inner = inner[1:-1]
    ids = []
    for part in re.split(r';', inner):
        rid = match_citation_part(part, ref_index)
        if rid and rid not in ids:
            ids.append(rid)
    return ids


def wrap_citations(fragment: str, ref_index: dict[str, list[str]]) -> str:
    soup = BeautifulSoup(fragment, 'html.parser')
    skip_tags = {'a', 'code', 'pre', 'script', 'style', 'figcaption', 'h1', 'h2', 'h3', 'h4'}
    # Parenthetical groups containing author-year patterns.
    parenthetical = re.compile(r'\((?=[^()]{0,220}(?:18|19|20)\d{2})[^()]{2,260}\)')
    narrative = re.compile(r"\b([A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ\-’']+(?:\s+(?:&|and)\s+[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ\-’']+|\s+et\s+al\.)?)\s+\(((?:18|19|20)\d{2}[a-z]?)\)")

    text_nodes = [n for n in soup.find_all(string=True) if n.strip() and not any(p.name in skip_tags for p in n.parents)]
    for node in text_nodes:
        text = str(node)
        matches: list[tuple[int, int, list[str]]] = []
        for m in parenthetical.finditer(text):
            ids = citation_ids(m.group(0), ref_index)
            if ids:
                matches.append((m.start(), m.end(), ids))
        for m in narrative.finditer(text):
            ids = citation_ids(f'{m.group(1)}, {m.group(2)}', ref_index)
            if ids:
                # Avoid overlap with an existing parenthetical match.
                if not any(not (m.end() <= a or m.start() >= b) for a, b, _ in matches):
                    matches.append((m.start(), m.end(), ids))
        if not matches:
            continue
        matches.sort(key=lambda x: x[0])
        parts: list[object] = []
        pos = 0
        for a, b, ids in matches:
            if a < pos:
                continue
            if a > pos:
                parts.append(NavigableString(text[pos:a]))
            span = soup.new_tag('span')
            span['class'] = ['citation-callout']
            span['tabindex'] = '0'
            span['role'] = 'button'
            span['data-ref-ids'] = ','.join(ids)
            span.string = text[a:b]
            parts.append(span)
            pos = b
        if pos < len(text):
            parts.append(NavigableString(text[pos:]))
        for p in reversed(parts):
            node.insert_after(p)
        node.extract()
    return str(soup)


def render_markdown(md_path: Path, html_path: Path) -> None:
    run(['pandoc', str(md_path), '-f', 'gfm+raw_html', '-t', 'html5', '--wrap=none', '-o', str(html_path)])


def add_document_nav(fragment: str, prev_doc: dict | None, next_doc: dict | None) -> str:
    soup = BeautifulSoup(fragment, 'html.parser')
    nav = soup.new_tag('nav')
    nav['class'] = ['document-nav']
    if prev_doc:
        b = soup.new_tag('button')
        b['class'] = ['document-nav-button', 'previous']
        b['data-doc'] = prev_doc['slug']
        b.string = f'← {prev_doc["short_title"]}'
        nav.append(b)
    else:
        nav.append(soup.new_tag('span'))
    if next_doc:
        b = soup.new_tag('button')
        b['class'] = ['document-nav-button', 'next']
        b['data-doc'] = next_doc['slug']
        b.string = f'{next_doc["short_title"]} →'
        nav.append(b)
    soup.append(nav)
    return str(soup)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / 'assets').mkdir(parents=True)
    (OUT / 'content' / 'html').mkdir(parents=True)
    (OUT / 'data').mkdir(parents=True)
    (OUT / 'figure').mkdir(parents=True)

    # Reconvert from the provided DOCX to keep the build reproducible.
    if WORK.exists():
        (WORK / 'media').mkdir(parents=True, exist_ok=True)
    run(['pandoc', str(SRC), '--extract-media=' + str(WORK / 'media'), '-t', 'gfm', '-o', str(FULL_MD)])
    full = FULL_MD.read_text(encoding='utf-8')

    # Parse the authoritative figure list and use it to correct body caption numbering.
    fig_seg = extract_between(full, '# List of Figures', '# List of Appendices')
    fig_pat = re.compile(r'\[Figure\s+([A-Z0-9.]+)\.\s+(.*?)(?:\[\d+\]\([^)]+\)\]\([^)]+\))', re.S)
    fig_entries = [{'number': n, 'caption': clean_inline_md(c)} for n, c in fig_pat.findall(fig_seg)]
    image_pat = re.compile(r'<img src="([^"]+)"[^>]*?/?>\s*\n\s*(?:<span[^>]*class="anchor"[^>]*></span>)?Figure\s+([A-Z0-9.]+)\.\s+(.*?)(?=\n\n)', re.S)
    image_counter = 0
    figures_data = []

    def figure_repl(m: re.Match) -> str:
        nonlocal image_counter
        entry = fig_entries[image_counter]
        src_rel = m.group(1)
        src = WORK / src_rel
        ext = src.suffix.lower()
        safe_no = entry['number'].lower().replace('.', '-').replace(' ', '-')
        filename = f'figure-{safe_no}{ext}'
        dst = OUT / 'figure' / filename
        shutil.copy2(src, dst)
        caption = entry['caption']
        figures_data.append({'number': entry['number'], 'caption': caption, 'file': filename})
        image_counter += 1
        alt = html.escape(caption, quote=True)
        cap_html = html.escape(caption)
        return (
            f'<figure id="figure-{safe_no}" class="dissertation-figure">\n'
            f'  <a class="figure-link" href="../figure/{filename}" data-figure-src="figure/{filename}" '
            f'data-figure-number="Figure {entry["number"]}." data-figure-caption="{alt}">\n'
            f'    <img src="../figure/{filename}" alt="{alt}" loading="lazy" />\n'
            f'  </a>\n'
            f'  <figcaption><strong>Figure {entry["number"]}.</strong> {cap_html}</figcaption>\n'
            f'</figure>'
        )

    full = image_pat.sub(figure_repl, full)
    if image_counter != len(fig_entries):
        raise RuntimeError(f'Figure mismatch: replaced {image_counter}, list has {len(fig_entries)}')
    write_text(OUT / 'data' / 'figures.json', json.dumps(figures_data, ensure_ascii=False, indent=2))

    # Front matter in requested order.
    abstract = '# Abstract\n\n' + strip_first_heading(extract_between(full, '# Abstract', '# List of Tables'))
    acknowledgement = '# Acknowledgment\n\n' + strip_first_heading(extract_between(full, '# Acknowledgement', '# Abstract'))
    epigraph = '# Epigraph\n\n' + strip_first_heading(extract_between(full, '# Epigraph', '# Acknowledgement'))

    title_md = f'''# {TITLE}\n\n<div class="title-page-meta">\n\n**{AUTHOR}**\n\nA Dissertation Submitted to the Faculty of  \nThe Dorothy F. Schmidt College of Arts and Letters\n\nIn Partial Fulfillment of the Requirements for the Degree of  \n{DEGREE}\n\n{INSTITUTION}  \nBoca Raton, FL\n\n{DATE}\n\n</div>\n\n<nav class="title-page-links" aria-label="Front matter">\n<button data-doc="abstract">Begin with the Abstract</button>\n<button data-doc="acknowledgment">Acknowledgment</button>\n<button data-doc="epigraph">Epigraph</button>\n</nav>\n'''

    chapter_specs = [
        ('chapter-1', 1, 'Chapter 1 — Introduction', '# — Introduction', '# — Literature Review and Theoretical Framework'),
        ('chapter-2', 2, 'Chapter 2 — Literature Review and Theoretical Framework', '# — Literature Review and Theoretical Framework', '# — Research Methodology'),
        ('chapter-3', 3, 'Chapter 3 — Research Methodology', '# — Research Methodology', '# PART II — Experimental and Theoretical Investigations'),
        ('chapter-4', 4, 'Chapter 4 — Ecological Intelligence and Vernacular Computation', '# — Ecological Intelligence and Vernacular Computation', '# Interlude I — Morphogenesis at the Edge of Possibility'),
        ('chapter-5', 5, 'Chapter 5 — Simplexity and CNC Fabrication: Low-Tech Material Intelligence', '# — Simplexity and CNC Fabrication: Low-Tech Material Intelligence', '# — Machinic Logic and Robot Material Practice'),
        ('chapter-6', 6, 'Chapter 6 — Machinic Logic and Robot Material Practice', '# — Machinic Logic and Robot Material Practice', '# Interlude II — Open-Source Robotic Ecologies as Technical Commons'),
        ('chapter-7', 7, 'Chapter 7 — Situated Robotic Fabrication as Feedback Continuum', '# — Situated Robotic Fabrication as Feedback Continuum', '# PART III — Synthesis, Discussion, and Conclusion'),
        ('chapter-8', 8, 'Chapter 8 — Discussion: Conditions, Tensions, and Horizons of the Design-to-Fabrication Continuum', '# — Discussion: Conditions, Tensions, and Horizons of the Design-to-Fabrication Continuum', '# — Conclusion and Future Work'),
        ('chapter-9', 9, 'Chapter 9 — Conclusion and Future Work', '# — Conclusion and Future Work', '# Appendices'),
    ]

    docs: list[dict] = [
        {'slug': 'title', 'title': TITLE, 'short_title': 'Title Page', 'type': 'title', 'md': title_md, 'sections': []},
        {'slug': 'abstract', 'title': 'Abstract', 'short_title': 'Abstract', 'type': 'front', 'md': abstract, 'sections': []},
        {'slug': 'acknowledgment', 'title': 'Acknowledgment', 'short_title': 'Acknowledgment', 'type': 'front', 'md': acknowledgement, 'sections': []},
        {'slug': 'epigraph', 'title': 'Epigraph', 'short_title': 'Epigraph', 'type': 'front', 'md': epigraph, 'sections': []},
    ]

    # Add chapters/interludes in dissertation order.
    for slug, no, heading, start, end in chapter_specs[:4]:
        raw = strip_first_heading(extract_between(full, start, end))
        raw, sections = number_chapter_headings(raw, no)
        docs.append({'slug': slug, 'title': heading, 'short_title': f'Chapter {no}', 'type': 'chapter', 'md': f'# {heading}\n\n{raw}', 'sections': sections})

    raw_i1 = strip_first_heading(extract_between(full, '# Interlude I — Morphogenesis at the Edge of Possibility', '# — Simplexity and CNC Fabrication: Low-Tech Material Intelligence'))
    raw_i1, sec_i1 = transform_interlude_headings(raw_i1, 'I')
    docs.append({'slug': 'interlude-1', 'title': 'Interlude I — Morphogenesis at the Edge of Possibility', 'short_title': 'Interlude I', 'type': 'interlude', 'md': '# Interlude I — Morphogenesis at the Edge of Possibility\n\n' + raw_i1, 'sections': sec_i1})

    for slug, no, heading, start, end in chapter_specs[4:6]:
        raw = strip_first_heading(extract_between(full, start, end))
        raw, sections = number_chapter_headings(raw, no)
        docs.append({'slug': slug, 'title': heading, 'short_title': f'Chapter {no}', 'type': 'chapter', 'md': f'# {heading}\n\n{raw}', 'sections': sections})

    raw_i2 = strip_first_heading(extract_between(full, '# Interlude II — Open-Source Robotic Ecologies as Technical Commons', '# — Situated Robotic Fabrication as Feedback Continuum'))
    raw_i2, sec_i2 = transform_interlude_headings(raw_i2, 'II')
    docs.append({'slug': 'interlude-2', 'title': 'Interlude II — Open-Source Robotic Ecologies as Technical Commons', 'short_title': 'Interlude II', 'type': 'interlude', 'md': '# Interlude II — Open-Source Robotic Ecologies as Technical Commons\n\n' + raw_i2, 'sections': sec_i2})

    for slug, no, heading, start, end in chapter_specs[6:]:
        raw = strip_first_heading(extract_between(full, start, end))
        raw, sections = number_chapter_headings(raw, no)
        docs.append({'slug': slug, 'title': heading, 'short_title': f'Chapter {no}', 'type': 'chapter', 'md': f'# {heading}\n\n{raw}', 'sections': sections})

    appendices_raw = extract_between(full, '# Appendices', '# Bibliography')
    for slug, heading, md in split_appendices(appendices_raw):
        docs.append({'slug': slug, 'title': heading, 'short_title': heading.split(' — ')[0], 'type': 'appendix', 'md': md, 'sections': []})

    bibliography_md = extract_between(full, '# Bibliography', None)
    refs = parse_bibliography(bibliography_md)
    ref_index = build_ref_index(refs)
    write_text(OUT / 'data' / 'references.json', json.dumps(refs, ensure_ascii=False, indent=2))

    # Bibliography Markdown with stable HTML anchors, while remaining readable on GitHub.
    bib_lines = ['# Bibliography', '']
    for ref in refs:
        bib_lines.append(f'<a id="{ref["id"]}"></a>')
        bib_lines.append('')
        bib_lines.append(ref['text'])
        bib_lines.append('')
    bibliography_clean_md = '\n'.join(bib_lines)
    write_text(OUT / 'content' / 'bibliography.md', bibliography_clean_md)

    # Write and render each source document.
    for doc in docs:
        md_path = OUT / 'content' / f'{doc["slug"]}.md'
        write_text(md_path, doc['md'])
        html_path = OUT / 'content' / 'html' / f'{doc["slug"]}.html'
        render_markdown(md_path, html_path)

    # Build bibliography HTML directly so stable IDs, highlighting, and external links remain exact.
    bib_html_path = OUT / 'content' / 'html' / 'bibliography.html'
    bib_parts = ['<h1 id="bibliography">Bibliography</h1>']
    for ref in refs:
        text = html.escape(ref['text'])
        for url in sorted(ref['urls'], key=len, reverse=True):
            escaped = html.escape(url)
            link = f'<a href="{escaped}" target="_blank" rel="noopener noreferrer">{escaped}</a>'
            text = text.replace(escaped, link)
        bib_parts.append(f'<article class="bibliography-entry" id="entry-{ref["id"]}"><p>{text}</p></article>')
    bib_html_path.write_text('\n'.join(bib_parts), encoding='utf-8')

    # Process HTML fragments: website-relative images, interactive citations, and prev/next document navigation.
    for idx, doc in enumerate(docs):
        html_path = OUT / 'content' / 'html' / f'{doc["slug"]}.html'
        fragment = html_path.read_text(encoding='utf-8')
        fragment = fragment.replace('../figure/', 'figure/')
        fragment = wrap_citations(fragment, ref_index)
        prev_doc = docs[idx - 1] if idx > 0 else None
        next_doc = docs[idx + 1] if idx + 1 < len(docs) else None
        fragment = add_document_nav(fragment, prev_doc, next_doc)
        html_path.write_text(fragment, encoding='utf-8')

    # Navigation: front matter and appendices stay in the reading sequence but are omitted from the simplified TOC.
    toc = [
        {'part': 'PART I — Theoretical and Methodological Framework', 'items': [
            {'slug': 'chapter-1', 'label': 'Chapter 1 — Introduction'},
            {'slug': 'chapter-2', 'label': 'Chapter 2 — Literature Review and Theoretical Framework'},
            {'slug': 'chapter-3', 'label': 'Chapter 3 — Research Methodology'},
        ]},
        {'part': 'PART II — Experimental and Theoretical Investigations', 'items': [
            {'slug': 'chapter-4', 'label': 'Chapter 4 — Ecological Intelligence and Vernacular Computation'},
            {'slug': 'interlude-1', 'label': 'Interlude I — Morphogenesis at the Edge of Possibility'},
            {'slug': 'chapter-5', 'label': 'Chapter 5 — Simplexity and CNC Fabrication: Low-Tech Material Intelligence'},
            {'slug': 'chapter-6', 'label': 'Chapter 6 — Machinic Logic and Robot Material Practice'},
            {'slug': 'interlude-2', 'label': 'Interlude II — Open-Source Robotic Ecologies as Technical Commons'},
            {'slug': 'chapter-7', 'label': 'Chapter 7 — Situated Robotic Fabrication as Feedback Continuum'},
        ]},
        {'part': 'PART III — Synthesis, Discussion, and Conclusion', 'items': [
            {'slug': 'chapter-8', 'label': 'Chapter 8 — Discussion: Conditions, Tensions, and Horizons of the Design-to-Fabrication Continuum'},
            {'slug': 'chapter-9', 'label': 'Chapter 9 — Conclusion and Future Work'},
        ]},
    ]
    manifest = [{k: d[k] for k in ['slug', 'title', 'short_title', 'type', 'sections']} for d in docs]
    write_text(OUT / 'data' / 'navigation.json', json.dumps({'toc': toc, 'documents': manifest}, ensure_ascii=False, indent=2))

    # Plain Markdown edition README.
    md_links = []
    for d in docs:
        if d['slug'] == 'title':
            continue
        md_links.append(f'- [{d["title"]}](content/{d["slug"]}.md)')
    md_links.append('- [Bibliography](content/bibliography.md)')
    write_text(OUT / 'MARKDOWN-EDITION.md', '# Dissertation — Markdown Edition\n\n' + '\n'.join(md_links) + '\n')

    write_text(OUT / 'index.html', INDEX_HTML)
    write_text(OUT / 'assets' / 'style.css', STYLE_CSS)
    write_text(OUT / 'assets' / 'app.js', APP_JS)
    write_text(OUT / '.nojekyll', '')
    write_text(OUT / 'README.md', README)

    # Include the build script in a tools folder for future updates.
    (OUT / 'tools').mkdir(exist_ok=True)
    shutil.copy2(Path(__file__), OUT / 'tools' / 'build_site.py')


INDEX_HTML = '''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="description" content="Dissertation by Celso Urroz" />
  <title>Design-to-Fabrication Continuum — Celso Urroz</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Funnel+Display:wght@400;600;700&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="assets/style.css" />
</head>
<body>
  <header class="site-header">
    <button id="homeTitle" class="site-title" aria-label="Return to the title page">Toward Design-to-Fabrication Continuum</button>
  </header>

  <div id="viewport" class="viewport">
    <div id="screenTrack" class="screen-track">
      <section id="tocScreen" class="screen toc-screen" aria-label="Table of contents">
        <div class="side-panel-scroll">
          <h1>Table of Contents</h1>
          <nav id="tocNav" class="toc-nav"></nav>
        </div>
      </section>

      <section id="readerScreen" class="screen reader-screen" aria-label="Dissertation reader">
        <main id="readerScroll" class="reader-scroll">
          <article id="readerContent" class="reader-content" aria-live="polite"></article>
        </main>
        <footer id="readerFooter" class="reader-footer">
          <span id="footerChapter" class="footer-chapter"></span>
          <span id="footerSection" class="footer-section"></span>
        </footer>
        <div id="progressControl" class="progress-control" aria-label="Reading progress">
          <div id="progressRail" class="progress-rail"><button id="progressDot" class="progress-dot" aria-label="Drag to scroll"></button></div>
        </div>
      </section>

      <section id="bibliographyScreen" class="screen bibliography-screen" aria-label="Bibliography">
        <div id="bibliographyScroll" class="side-panel-scroll bibliography-scroll">
          <article id="bibliographyContent" class="bibliography-content"></article>
        </div>
      </section>
    </div>
  </div>

  <button id="leftArrow" class="screen-arrow screen-arrow-left" aria-label="Open table of contents">‹</button>
  <button id="rightArrow" class="screen-arrow screen-arrow-right" aria-label="Open bibliography">›</button>
  <div id="citationPopup" class="citation-popup" role="dialog" aria-label="Citation details"></div>

  <dialog id="figureDialog" class="figure-dialog">
    <button id="closeFigure" class="close-figure" aria-label="Close figure">×</button>
    <div class="figure-dialog-inner">
      <img id="figureDialogImage" alt="" />
      <p id="figureDialogCaption"></p>
    </div>
  </dialog>

  <script src="assets/app.js" defer></script>
</body>
</html>
'''

STYLE_CSS = r''':root {
  --font-ui: "Funnel Display", Arial, sans-serif;
  --font-body: "Funnel Display", Arial, sans-serif;
  --background: #ffffff;
  --foreground: #000000;
  --muted: #6f6f6f;
  --panel: rgba(0, 0, 0, 0.86);
  --panel-text: #ffffff;
  --corner: 8px;
  --header-height: 64px;
  --footer-height: 54px;
  --reading-width: 760px;
  --body-size: 18px;
  --body-leading: 1.72;
  --transition: 0.36s cubic-bezier(.22,.72,.23,1);
}

* { box-sizing: border-box; }
html, body { height: 100%; }
html { background: var(--background); }
body {
  margin: 0;
  overflow: hidden;
  color: var(--foreground);
  background: var(--background);
  font-family: var(--font-body);
}
button, input { font: inherit; }
button { color: inherit; }

.site-header {
  position: fixed;
  inset: 0 0 auto 0;
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 72px;
  background: rgba(255,255,255,.94);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(0,0,0,.12);
  z-index: 1000;
}
.site-title {
  max-width: min(820px, 80vw);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  border: 0;
  padding: 8px 12px;
  background: transparent;
  font-family: var(--font-ui);
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
}
.site-title:hover { text-decoration: underline; text-underline-offset: 4px; }

.viewport { position: fixed; inset: var(--header-height) 0 0; overflow: hidden; }
.screen-track {
  height: 100%;
  width: 300%;
  display: flex;
  transform: translate3d(-33.333333%,0,0);
  transition: transform var(--transition);
  will-change: transform;
}
.screen { position: relative; width: 33.333333%; height: 100%; flex: 0 0 33.333333%; overflow: hidden; background: var(--background); }
.side-panel-scroll, .reader-scroll {
  height: 100%;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: none;
}
.side-panel-scroll::-webkit-scrollbar, .reader-scroll::-webkit-scrollbar { width: 0; height: 0; }
.side-panel-scroll { padding: 70px max(7vw, 36px) 100px; }
.side-panel-scroll > h1, .bibliography-content > h1 { margin: 0 0 48px; font-size: clamp(34px, 5vw, 72px); line-height: 1; }

.toc-nav { max-width: 920px; margin: 0 auto; }
.toc-group { margin: 0 0 42px; }
.toc-part { margin: 0 0 14px; font-size: 13px; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; }
.toc-item {
  display: block;
  width: 100%;
  border: 0;
  border-top: 1px solid rgba(0,0,0,.18);
  padding: 14px 0;
  text-align: left;
  background: transparent;
  cursor: pointer;
  font-size: clamp(17px, 2vw, 24px);
  line-height: 1.2;
  transition: padding-left .2s ease, background-color .2s ease;
}
.toc-item:last-child { border-bottom: 1px solid rgba(0,0,0,.18); }
.toc-item:hover, .toc-item.active { padding-left: 12px; background: rgba(0,0,0,.045); }

.reader-scroll { padding: 56px 72px calc(var(--footer-height) + 76px); }
.reader-content { width: min(var(--reading-width), 100%); margin: 0 auto; font-size: var(--body-size); line-height: var(--body-leading); }
.reader-content > h1 { font-size: clamp(38px, 5vw, 70px); line-height: 1.02; letter-spacing: -.025em; margin: 8vh 0 60px; }
.reader-content h2 { font-size: clamp(27px, 3vw, 38px); line-height: 1.13; margin: 80px 0 24px; scroll-margin-top: 96px; }
.reader-content h3 { font-size: clamp(21px, 2vw, 28px); line-height: 1.2; margin: 52px 0 20px; scroll-margin-top: 96px; }
.reader-content p { margin: 0 0 1.25em; }
.reader-content blockquote { margin: 40px 0; padding-left: 24px; border-left: 2px solid #000; font-size: 1.12em; }
.reader-content a { color: inherit; text-decoration-thickness: 1px; text-underline-offset: 3px; }
.reader-content ul, .reader-content ol { padding-left: 1.4em; }
.reader-content table { width: 100%; border-collapse: collapse; display: block; overflow-x: auto; margin: 36px 0; font-size: .88em; }
.reader-content th, .reader-content td { border: 1px solid #000; padding: 9px 11px; vertical-align: top; }

.title-page-meta { margin: 12vh 0 8vh; font-size: clamp(17px, 2vw, 23px); line-height: 1.45; }
.title-page-links { display: flex; flex-wrap: wrap; gap: 10px; }
.title-page-links button, .document-nav-button {
  background: #fff;
  color: #000;
  border: 2px solid #000;
  border-radius: 6px;
  padding: 9px 15px;
  cursor: pointer;
  transition: background .2s ease, color .2s ease;
}
.title-page-links button:hover, .document-nav-button:hover { background: #000; color: #fff; }

.dissertation-figure { margin: 58px min(-6vw, -40px); }
.dissertation-figure img { display: block; width: 100%; max-height: 78vh; object-fit: contain; background: #f4f4f4; }
.figure-link { display: block; cursor: zoom-in; }
.dissertation-figure figcaption { margin-top: 14px; font-size: .84em; line-height: 1.42; }

.citation-callout {
  border-bottom: 1px dotted #000;
  cursor: pointer;
  white-space: normal;
}
.citation-callout:hover, .citation-callout:focus { background: #000; color: #fff; outline: 2px solid #000; outline-offset: 1px; }
.citation-popup {
  position: fixed;
  display: none;
  z-index: 1800;
  max-width: min(50vw, 760px);
  padding: 10px 14px;
  border-radius: var(--corner);
  background: var(--panel);
  color: var(--panel-text);
  font-family: var(--font-ui);
  font-size: 14px;
  line-height: 1.25;
  box-shadow: 0 10px 30px rgba(0,0,0,.2);
}
.citation-popup.visible { display: block; }
.citation-popup button {
  display: block;
  width: 100%;
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: #fff;
  text-align: left;
  white-space: nowrap;
  cursor: pointer;
}
.citation-popup button:hover { text-decoration: underline; text-underline-offset: 3px; }

.reader-footer {
  position: absolute;
  inset: auto 0 0 0;
  height: var(--footer-height);
  padding: 0 28px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
  background: rgba(255,255,255,.95);
  backdrop-filter: blur(10px);
  border-top: 1px solid rgba(0,0,0,.14);
  font-family: var(--font-ui);
  font-size: 13px;
  transition: opacity .2s ease, transform .2s ease;
  z-index: 30;
}
.reader-footer.hidden { opacity: 0; transform: translateY(100%); pointer-events: none; }
.footer-chapter { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.footer-section { white-space: nowrap; }

.progress-control { position: absolute; right: 19px; top: 50%; width: 32px; height: 350px; transform: translateY(-50%); z-index: 40; }
.progress-rail { position: absolute; left: 15px; top: 0; width: 2px; height: 100%; background: rgba(0,0,0,.9); cursor: pointer; }
.progress-dot { position: absolute; left: 50%; top: 0; width: 18px; height: 18px; padding: 0; border: 0; border-radius: 50%; background: #000; transform: translate(-50%, -50%); cursor: grab; }
.progress-dot:active { cursor: grabbing; }
.progress-control.hidden { opacity: 0; pointer-events: none; }

.screen-arrow {
  position: fixed;
  top: 50%;
  z-index: 1200;
  width: 48px;
  height: 72px;
  transform: translateY(-50%);
  border: 0;
  background: transparent;
  font-size: 54px;
  font-weight: 400;
  line-height: 1;
  cursor: pointer;
  transition: opacity .2s ease, transform .2s ease;
}
.screen-arrow:hover { transform: translateY(-50%) scale(1.08); }
.screen-arrow-left { left: 8px; }
.screen-arrow-right { right: 52px; }
.screen-arrow.hidden { opacity: 0; pointer-events: none; }

.bibliography-content { max-width: 920px; margin: 0 auto; }
.bibliography-entry { padding: 18px 20px; margin: 0 -20px 8px; border-radius: var(--corner); transition: background .2s ease, color .2s ease; }
.bibliography-entry p { margin: 0; line-height: 1.5; }
.bibliography-entry.highlighted { background: #000; color: #fff; }
.bibliography-entry.highlighted a { color: #fff; }

.document-nav { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; align-items: center; margin: 110px 0 20px; padding-top: 26px; border-top: 1px solid rgba(0,0,0,.18); }
.document-nav .next { justify-self: end; text-align: right; }

.figure-dialog { width: 100vw; max-width: none; height: 100vh; max-height: none; margin: 0; padding: 0; border: 0; background: rgba(0,0,0,.92); color: #fff; }
.figure-dialog::backdrop { background: transparent; }
.figure-dialog-inner { height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; padding: 58px; }
.figure-dialog img { max-width: 92vw; max-height: 78vh; object-fit: contain; }
.figure-dialog p { max-width: 920px; margin: 0; text-align: center; font-size: 14px; }
.close-figure { position: fixed; right: 20px; top: 12px; border: 0; background: transparent; color: #fff; font-size: 46px; cursor: pointer; }

@media (max-width: 899px) {
  :root { --header-height: 56px; --body-size: 17px; --body-leading: 1.65; }
  .site-header { padding: 0 54px; }
  .site-title { max-width: 76vw; font-size: 13px; }
  .reader-scroll { padding: 34px 48px calc(var(--footer-height) + 62px); }
  .reader-content > h1 { margin-top: 5vh; }
  .side-panel-scroll { padding: 52px 48px 90px; }
  .dissertation-figure { margin: 48px 0; }
  .progress-control { display: none; }
  .screen-arrow { width: 40px; font-size: 44px; }
  .screen-arrow-left { left: 0; }
  .screen-arrow-right { right: 0; }
  .citation-popup { max-width: calc(100vw - 32px); font-size: 13px; }
  .citation-popup button { white-space: normal; }
  .reader-footer { padding: 0 18px; }
  .figure-dialog-inner { padding: 50px 18px 24px; }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
'''

APP_JS = r'''const state = {
  screen: 1,
  currentDoc: 'title',
  navigation: null,
  references: new Map(),
  documents: new Map(),
  scrollPositions: new Map(),
  activeSections: [],
};

const el = {};

async function init() {
  Object.assign(el, {
    track: document.getElementById('screenTrack'),
    viewport: document.getElementById('viewport'),
    readerScroll: document.getElementById('readerScroll'),
    readerContent: document.getElementById('readerContent'),
    bibliographyScroll: document.getElementById('bibliographyScroll'),
    bibliographyContent: document.getElementById('bibliographyContent'),
    tocNav: document.getElementById('tocNav'),
    footer: document.getElementById('readerFooter'),
    footerChapter: document.getElementById('footerChapter'),
    footerSection: document.getElementById('footerSection'),
    leftArrow: document.getElementById('leftArrow'),
    rightArrow: document.getElementById('rightArrow'),
    homeTitle: document.getElementById('homeTitle'),
    popup: document.getElementById('citationPopup'),
    progressControl: document.getElementById('progressControl'),
    progressRail: document.getElementById('progressRail'),
    progressDot: document.getElementById('progressDot'),
    figureDialog: document.getElementById('figureDialog'),
    figureImage: document.getElementById('figureDialogImage'),
    figureCaption: document.getElementById('figureDialogCaption'),
    closeFigure: document.getElementById('closeFigure'),
  });

  const [navData, refs, bibHtml] = await Promise.all([
    fetch('data/navigation.json').then(r => r.json()),
    fetch('data/references.json').then(r => r.json()),
    fetch('content/html/bibliography.html').then(r => r.text()),
  ]);
  state.navigation = navData;
  navData.documents.forEach(d => state.documents.set(d.slug, d));
  refs.forEach(r => state.references.set(r.id, r));
  el.bibliographyContent.innerHTML = bibHtml;
  buildToc(navData.toc);
  bindEvents();

  const hash = location.hash.replace(/^#/, '');
  const initial = state.documents.has(hash) ? hash : 'title';
  await loadDocument(initial, false);
  setScreen(1, false);
}

function buildToc(groups) {
  el.tocNav.innerHTML = '';
  groups.forEach(group => {
    const section = document.createElement('section');
    section.className = 'toc-group';
    const part = document.createElement('div');
    part.className = 'toc-part';
    part.textContent = group.part;
    section.append(part);
    group.items.forEach(item => {
      const button = document.createElement('button');
      button.className = 'toc-item';
      button.dataset.doc = item.slug;
      button.textContent = item.label;
      section.append(button);
    });
    el.tocNav.append(section);
  });
}

async function loadDocument(slug, pushHistory = true) {
  if (!state.documents.has(slug)) return;
  if (state.currentDoc) state.scrollPositions.set(state.currentDoc, el.readerScroll.scrollTop);
  closeCitationPopup();
  const html = await fetch(`content/html/${slug}.html`).then(r => r.text());
  state.currentDoc = slug;
  el.readerContent.innerHTML = html;
  const doc = state.documents.get(slug);
  el.footerChapter.textContent = doc.title;
  state.activeSections = [...el.readerContent.querySelectorAll('h2, h3')];
  updateFooterSection();
  updateTocActive();
  bindDynamicContent();
  const saved = state.scrollPositions.get(slug) || 0;
  requestAnimationFrame(() => {
    el.readerScroll.scrollTop = saved;
    updateProgress();
    updateFooterVisibility();
  });
  if (pushHistory) history.pushState({doc: slug}, '', `#${slug}`);
}

function bindDynamicContent() {
  el.readerContent.querySelectorAll('[data-doc]').forEach(button => {
    button.addEventListener('click', async () => {
      await loadDocument(button.dataset.doc);
      setScreen(1);
    });
  });
  el.readerContent.querySelectorAll('.citation-callout').forEach(c => {
    c.addEventListener('click', e => { e.stopPropagation(); openCitationPopup(c); });
    c.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); openCitationPopup(c); } });
  });
  el.readerContent.querySelectorAll('.figure-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      el.figureImage.src = link.dataset.figureSrc;
      el.figureImage.alt = link.dataset.figureCaption || '';
      el.figureCaption.textContent = `${link.dataset.figureNumber} ${link.dataset.figureCaption}`;
      el.figureDialog.showModal();
    });
  });
}

function openCitationPopup(target) {
  const ids = (target.dataset.refIds || '').split(',').filter(Boolean);
  el.popup.innerHTML = '';
  ids.forEach(id => {
    const ref = state.references.get(id);
    if (!ref) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = ref.display;
    button.addEventListener('click', () => openReference(id));
    el.popup.append(button);
  });
  if (!el.popup.children.length) return;
  el.popup.classList.add('visible');
  const rect = target.getBoundingClientRect();
  const popRect = el.popup.getBoundingClientRect();
  let left = rect.left;
  let top = rect.bottom + 8;
  if (left + popRect.width > innerWidth - 12) left = innerWidth - popRect.width - 12;
  if (left < 12) left = 12;
  if (top + popRect.height > innerHeight - 12) top = rect.top - popRect.height - 8;
  el.popup.style.left = `${left}px`;
  el.popup.style.top = `${Math.max(12, top)}px`;
}

function closeCitationPopup() { el.popup.classList.remove('visible'); }

function openReference(id) {
  closeCitationPopup();
  setScreen(2);
  requestAnimationFrame(() => {
    const entry = document.getElementById(`entry-${id}`);
    if (!entry) return;
    document.querySelectorAll('.bibliography-entry.highlighted').forEach(x => x.classList.remove('highlighted'));
    entry.classList.add('highlighted');
    const containerRect = el.bibliographyScroll.getBoundingClientRect();
    const entryRect = entry.getBoundingClientRect();
    const targetTop = Math.max(0, el.bibliographyScroll.scrollTop + entryRect.top - containerRect.top - (el.bibliographyScroll.clientHeight - entryRect.height) / 2);
    el.bibliographyScroll.scrollTop = targetTop;
    setTimeout(() => entry.classList.remove('highlighted'), 3200);
  });
}

function setScreen(index, animate = true) {
  state.screen = Math.max(0, Math.min(2, index));
  if (!animate) el.track.style.transition = 'none';
  el.track.style.transform = `translate3d(${-state.screen * 33.333333}%,0,0)`;
  if (!animate) requestAnimationFrame(() => el.track.style.transition = '');
  updateArrows();
  updateFooterVisibility();
  closeCitationPopup();
}

function updateArrows() {
  el.leftArrow.classList.toggle('hidden', state.screen === 0);
  el.rightArrow.classList.toggle('hidden', state.screen === 2);
  el.leftArrow.setAttribute('aria-label', state.screen === 2 ? 'Return to reading' : 'Open table of contents');
  el.rightArrow.setAttribute('aria-label', state.screen === 0 ? 'Return to reading' : 'Open bibliography');
}

function updateFooterVisibility() {
  const hidden = state.screen !== 1 || state.currentDoc === 'title';
  el.footer.classList.toggle('hidden', hidden);
  el.progressControl.classList.toggle('hidden', hidden);
}

function updateTocActive() {
  document.querySelectorAll('.toc-item').forEach(x => x.classList.toggle('active', x.dataset.doc === state.currentDoc));
}

function updateFooterSection() {
  const headings = state.activeSections;
  if (!headings.length) { el.footerSection.textContent = ''; return; }
  const y = el.readerScroll.scrollTop + 140;
  let idx = 0;
  headings.forEach((h, i) => { if (h.offsetTop <= y) idx = i; });
  el.footerSection.textContent = `Section ${idx + 1} / ${headings.length}`;
}

function updateProgress() {
  const max = el.readerScroll.scrollHeight - el.readerScroll.clientHeight;
  const ratio = max > 0 ? el.readerScroll.scrollTop / max : 0;
  el.progressDot.style.top = `${ratio * 100}%`;
  updateFooterSection();
}

function bindProgressDrag() {
  let dragging = false;
  const setFromClientY = y => {
    const r = el.progressRail.getBoundingClientRect();
    const ratio = Math.max(0, Math.min(1, (y - r.top) / r.height));
    const max = el.readerScroll.scrollHeight - el.readerScroll.clientHeight;
    el.readerScroll.scrollTop = ratio * Math.max(0, max);
  };
  el.progressRail.addEventListener('pointerdown', e => { dragging = true; el.progressRail.setPointerCapture(e.pointerId); setFromClientY(e.clientY); });
  el.progressRail.addEventListener('pointermove', e => { if (dragging) setFromClientY(e.clientY); });
  el.progressRail.addEventListener('pointerup', () => dragging = false);
  el.progressRail.addEventListener('pointercancel', () => dragging = false);
}

function bindSwipe() {
  let startX = 0, startY = 0, active = false;
  el.viewport.addEventListener('pointerdown', e => {
    if (e.target.closest('button, a, .citation-callout, input, dialog')) return;
    startX = e.clientX; startY = e.clientY; active = true;
  });
  el.viewport.addEventListener('pointerup', e => {
    if (!active) return;
    active = false;
    const dx = e.clientX - startX, dy = e.clientY - startY;
    if (Math.abs(dx) > 70 && Math.abs(dx) > Math.abs(dy) * 1.25) setScreen(state.screen + (dx < 0 ? 1 : -1));
  });
  el.viewport.addEventListener('wheel', e => {
    if (Math.abs(e.deltaX) > 50 && Math.abs(e.deltaX) > Math.abs(e.deltaY) * 1.4) {
      e.preventDefault();
      setScreen(state.screen + (e.deltaX > 0 ? 1 : -1));
    }
  }, {passive: false});
}

function bindEvents() {
  el.homeTitle.addEventListener('click', async () => { await loadDocument('title'); setScreen(1); });
  el.leftArrow.addEventListener('click', () => setScreen(state.screen === 2 ? 1 : 0));
  el.rightArrow.addEventListener('click', () => setScreen(state.screen === 0 ? 1 : 2));
  el.tocNav.addEventListener('click', async e => {
    const button = e.target.closest('[data-doc]');
    if (!button) return;
    await loadDocument(button.dataset.doc);
    setScreen(1);
  });
  el.readerScroll.addEventListener('scroll', updateProgress, {passive: true});
  document.addEventListener('click', e => { if (!e.target.closest('.citation-popup, .citation-callout')) closeCitationPopup(); });
  el.closeFigure.addEventListener('click', () => el.figureDialog.close());
  el.figureDialog.addEventListener('click', e => { if (e.target === el.figureDialog) el.figureDialog.close(); });
  addEventListener('keydown', e => { if (e.key === 'Escape') closeCitationPopup(); });
  addEventListener('popstate', async () => { const slug = location.hash.replace(/^#/, '') || 'title'; if (state.documents.has(slug)) { await loadDocument(slug, false); setScreen(1); } });
  bindProgressDrag();
  bindSwipe();
}

init().catch(err => {
  console.error(err);
  document.body.innerHTML = `<pre style="padding:2rem">The dissertation site could not load. ${String(err)}</pre>`;
});
'''

README = f'''# Dissertation Website

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
:root {{
  --font-ui: "Funnel Display", Arial, sans-serif;
  --font-body: "Funnel Display", Arial, sans-serif;
  --background: #ffffff;
  --foreground: #000000;
  --panel: rgba(0, 0, 0, 0.86);
  --corner: 8px;
  --reading-width: 760px;
  --body-size: 18px;
}}
```

The initial style follows the visual language of the literature graph: Funnel Display, white background, black controls, dark translucent information panels, rounded 8 px corners, short 0.2-second interface transitions, and a thin vertical rail with a circular thumb.

## Update from a later DOCX

The script used for this conversion is included at `tools/build_site.py`. Update its `SRC` path and run it in an environment with Python, `python-docx`, Beautiful Soup, and Pandoc installed.
'''


if __name__ == '__main__':
    main()
