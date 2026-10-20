#!/usr/bin/env python3
"""Link every elaborated identifier in the Lean code to its declaration.

Uses verification/lean-references/references.json, which records Lean's own
.ilean reference data (see extract-lean-references.py); no name is resolved
lexically. Links are added to the Lean blocks of index.html and to every
bundled source page; project and AlgebraicAnalysis declarations open their
bundled page, other declarations their pinned GitHub source. The script is
idempotent and is run by rebuild.py after the generator.
"""
from pathlib import Path
import html, json, os, re, sys

root = Path(__file__).resolve().parent.parent
DATA = root / 'verification/lean-references/references.json'
PAGES = {'formal': 'sources/formal', 'library': 'sources/library'}
PAGE_CSS = 'a.ref{color:#0645ad;text-decoration:none}a.ref:hover{text-decoration:underline}'
INDEX_CSS = ('.lean-src a.lean-ref{color:inherit;text-decoration:underline dotted;'
             'text-decoration-color:var(--muted,#888);text-underline-offset:2px}'
             '.lean-src a.lean-ref:hover{text-decoration-style:solid}')


def load():
    data = json.loads(DATA.read_text())
    by_line = {}
    for key, spans in data['files'].items():
        lines = by_line[key] = {}
        for line, col, length, target in spans:
            lines.setdefault(line, []).append((col, length, target))
    return data, by_line


def href(data, target, here):
    name, repo, path, line = data['targets'][target]
    if repo in PAGES:
        rel = os.path.relpath(root / PAGES[repo] / (path + '.html'), here)
        return f'{rel if rel.startswith(".") else "./" + rel}#L{line}'
    return f'{data["urls"][repo]}{path}#L{line}'


def link_text(data, text, spans, here, cls):
    """Escape one line of source text and wrap the recorded references."""
    out, pos = [], 0
    for col, length, target in sorted(spans):
        if col < pos or col + length > len(text):
            continue
        name = data['targets'][target][0]
        out.append(html.escape(text[pos:col], quote=False))
        out.append(f'<a class="{cls}" href="{html.escape(href(data, target, here))}" '
                   f'title="{html.escape(name)}">{html.escape(text[col:col + length], quote=False)}</a>')
        pos = col + length
    out.append(html.escape(text[pos:], quote=False))
    return ''.join(out)


LINE = re.compile(r'<span id="L(\d+)"><a href="#L\1">\1</a> (.*?)</span>(?=\n|</pre>)')


def plain(fragment):
    return html.unescape(re.sub(r'<[^>]+>', '', fragment))


def link_page(data, by_line, repo, page):
    rel = str(page.relative_to(root / PAGES[repo]))[:-len('.html')]
    spans = by_line.get(f'{repo}:{rel}')
    if spans is None:
        return 0
    text = page.read_text()
    count = 0
    def line(m):
        nonlocal count
        n, body = int(m[1]), plain(m[2])
        found = spans.get(n, [])
        count += len(found)
        return (f'<span id="L{n}"><a href="#L{n}">{n}</a> '
                f'{link_text(data, body, found, page.parent, "ref")}</span>')
    head, sep, rest = text.partition('<pre>')
    if PAGE_CSS not in head:
        head = head.replace('</style>', PAGE_CSS + '</style>', 1)
    page.write_text(head + sep + LINE.sub(line, rest))
    return count


SOURCE = re.compile(r'href="([^"]+?)#L(\d+)(?:-L\d+)?"')
BLOCK = re.compile(r'<pre class="lean-src">(.*?)</pre>', re.S)


def source_key(data, url):
    if url.startswith('./sources/formal/'):
        return 'formal:' + url[len('./sources/formal/'):-len('.html')]
    for repo, base in data['urls'].items():
        if url.startswith(base):
            return f'{repo}:{url[len(base):]}'
    lib = 'https://github.com/itpplasma/algebraic-analysis/blob/' + data['library_commit'] + '/'
    if url.startswith(lib):
        return 'library:' + url[len(lib):]
    return None


def link_block(data, by_line, body, start, spans, stats):
    """Insert links into one generator block that starts at source line `start`."""
    pieces = re.split(r'(<[^>]+>)', body)
    out, line, col, inside = [], start, 0, 0
    for piece in pieces:
        if piece.startswith('<'):
            if re.match(r'<a[\s>]', piece):
                inside += 1
            elif piece == '</a>':
                inside -= 1
            out.append(piece)
            continue
        raw = html.unescape(piece)
        chunks = raw.split('\n')
        rendered = []
        for i, chunk in enumerate(chunks):
            if i:
                line, col = line + 1, 0
            if inside:
                stats['existing'] += sum(1 for c, l, _ in spans.get(line, ()) if col <= c < col + len(chunk))
                rendered.append(html.escape(chunk, quote=False))
            else:
                local = [(c - col, l, t) for c, l, t in spans.get(line, ())
                         if c >= col and c + l <= col + len(chunk)]
                stats['linked'] += len(local)
                rendered.append(link_text(data, chunk, local, root, 'lean-ref'))
            col += len(chunk)
        out.append('\n'.join(rendered))
    return ''.join(out)


def link_index(data, by_line):
    index = root / 'index.html'
    text = index.read_text()
    stats = dict(linked=0, existing=0, blocks=0, unmatched=0, unknown=0)
    out, pos = [], 0
    for m in BLOCK.finditer(text):
        before = text[pos:m.start()]
        sources = list(SOURCE.finditer(text, max(0, m.start() - 4000), m.start()))
        out.append(before)
        pos = m.end()
        body = re.sub(r'<a class="lean-ref"[^>]*>(.*?)</a>', r'\1', m[1])
        # The generator links only the namespace of a dotted name such as
        # `FreeAlgebra.ι`; Lean's reference covers the whole name instead.
        body = re.sub(r'<a class="definition-link" href="[^"]*">([^<]*\.)</a>(?=[^\s{(<.])', r'\1', body)
        key = source_key(data, sources[-1][1]) if sources else None
        spans = by_line.get(key) if key else None
        if spans is None:
            stats['unknown'] += 1
            out.append(m[0].replace(m[1], body))
            continue
        start = int(sources[-1][2])
        source_lines = data_text(key)
        block_lines = plain(body).split('\n')
        # The generator may cut a line short; columns stay valid for a prefix.
        window = (source_lines or [])[start - 1:start - 1 + len(block_lines)]
        if source_lines is not None and (len(window) != len(block_lines) or
                                         not all(s.startswith(b) for b, s in zip(block_lines, window))):
            stats['unmatched'] += 1
            out.append(m[0].replace(m[1], body))
            continue
        stats['blocks'] += 1
        out.append('<pre class="lean-src">' + link_block(data, by_line, body, start, spans, stats) + '</pre>')
    out.append(text[pos:])
    text = ''.join(out)
    if INDEX_CSS not in text:
        text = text.replace('</style>', INDEX_CSS + '</style>', 1)
    index.write_text(text)
    return stats


_texts = {}
def data_text(key):
    """Source lines of a bundled page, or the recorded text of a GitHub file."""
    if key not in _texts:
        repo, rel = key.split(':', 1)
        page = root / PAGES.get(repo, '-') / (rel + '.html')
        _texts[key] = ([plain(m[2]) for m in LINE.finditer(page.read_text())]
                       if repo in PAGES and page.exists() else _data['texts'].get(key))
    return _texts[key]


_data = {}


def main():
    data, by_line = load()
    _data.update(data)
    stats = link_index(data, by_line)
    pages = refs = 0
    for repo, base in PAGES.items():
        for page in sorted((root / base).rglob('*.lean.html')):
            refs += link_page(data, by_line, repo, page)
            pages += 1
    print(f'index.html: {stats["linked"]} links in {stats["blocks"]} Lean blocks '
          f'({stats["existing"]} references already linked to definition panels, '
          f'{stats["unknown"]} blocks without reference data, {stats["unmatched"]} blocks differing from source); '
          f'{refs} links in {pages} source pages.')
    if stats['unmatched']:
        sys.exit('some Lean blocks do not match their source lines')


if __name__ == '__main__':
    main()
