#!/usr/bin/env python3
"""Record Lean's own identifier references for the reviewer pages.

Reads the .ilean files of a *built* formal checkout at the pinned commit:
every identifier occurrence that Lean elaborated to a constant, together
with the module and line that declare it, as reported by Lean itself
(scripts/LeanDeclRanges.lean). No name is resolved lexically. Writes
verification/lean-references/references.json and plain source pages for
project and AlgebraicAnalysis files that have none yet. Run
scripts/link-lean-references.py afterwards to add the links.
"""
from pathlib import Path
import argparse, html, json, re, subprocess

root = Path(__file__).resolve().parent.parent
OUT = root / 'verification/lean-references/references.json'
STYLE = ('body{font:14px monospace}pre span{display:block}pre span:target{background:#fff0ad}'
         'a{color:#666}pre{white-space:pre-wrap}')


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True)


def utf16_to_index(line, col):
    """Convert an LSP UTF-16 column to a code point index."""
    units = 0
    for i, ch in enumerate(line):
        if units >= col:
            return i
        units += 2 if ord(ch) > 0xFFFF else 1
    return len(line)


def page(file, label, commit, text):
    """The generator's source page format (paper-lean-audit build.mjs)."""
    esc = lambda s: html.escape(s, quote=False).replace('"', '&quot;')
    lines = '\n'.join(f'<span id="L{i}"><a href="#L{i}">{i}</a> {esc(line)}</span>'
                      for i, line in enumerate(text.split('\n'), 1))
    return (f'<!doctype html><meta charset="utf-8"><title>{esc(file)}</title><style>{STYLE}</style>'
            f'<h1>{esc(file)}</h1><p>{esc(label)} · {esc(commit)}</p><pre>{lines}</pre>')


PROOF_KEYWORDS = ('theorem', 'lemma', 'instance', 'example')
DECL = re.compile(r'(?:@\[[^\]]*\]\s*)*(?:(?:private|protected|noncomputable|partial|unsafe|nonrec|public)\s+)*'
                  r'(theorem|lemma|instance|example|def|abbrev|structure|class|inductive|opaque|axiom)\b')


def preview(text_lines, start):
    """Doc comment (at most 4 lines) and declaration (at most 14 lines) starting
    at `start`. Theorems stop at `:=`; definitions keep their body up to a
    blank line or the next top-level command."""
    out, i = [], start - 1
    if i < len(text_lines) and text_lines[i].lstrip().startswith('/--'):
        doc = []
        while i < len(text_lines):
            doc.append(text_lines[i])
            i += 1
            if '-/' in doc[-1]:
                break
        out = doc if len(doc) <= 4 else doc[:3] + ['  …', doc[-1]]
    head = DECL.match(text_lines[i].strip()) if i < len(text_lines) else None
    proof = head is None or head[1] in PROOF_KEYWORDS
    for k, line in enumerate(text_lines[i:i + 14]):
        if k and (not line.strip() or (line[:1].strip() and not line.startswith(('|', ')')))):
            return '\n'.join(out)
        cut = line.find(':=')
        if proof and cut >= 0:
            out.append(line[:cut + 2])
            return '\n'.join(out)
        out.append(line)
        body = line.strip()
        if proof and (body.endswith(' where') or body == 'where'):
            return '\n'.join(out)
    more = i + 14 < len(text_lines) and text_lines[i + 14].strip() and not text_lines[i + 14][:1].strip()
    return '\n'.join(out + (['…'] if more or proof else []))


def add_previews(roots, targets, start, previews):
    sources = {r[0]: r[1] for r in roots}
    cache = {}
    for i in range(start, len(targets)):
        name, repo, rel, line = targets[i]
        if (repo, rel) not in cache:
            path = sources[repo] / rel
            cache[repo, rel] = path.read_text().split('\n') if path.exists() else None
        if cache[repo, rel]:
            previews[i] = preview(cache[repo, rel], line)


def checkout_roots(checkout, key, url, prefix):
    """Module roots of a built checkout: (repo key, source dir, ilean dir, link base).
    Keys without a link base get bundled pages; the others link to GitHub."""
    lake = json.loads((checkout / 'lake-manifest.json').read_text())
    roots = [(key, checkout, checkout / '.lake/build/lib/lean', url)]
    for pkg in lake['packages']:
        pdir = checkout / '.lake/packages' / pkg['name']
        if git(pdir, 'rev-parse', 'HEAD').strip() != pkg['rev']:
            raise SystemExit(f'package {pkg["name"]} is not at its manifest revision')
        name = 'library' if pkg['name'] == 'algebraicAnalysis' and not prefix else prefix + pkg['name']
        roots.append((name, pdir, pdir / '.lake/build/lib/lean',
                      pkg['url'].removesuffix('.git') + '/blob/' + pkg['rev'] + '/'))
    toolchain = (checkout / 'lean-toolchain').read_text().strip()
    tc_dir = Path.home() / '.elan/toolchains' / toolchain.replace('/', '--').replace(':', '---')
    roots.append((prefix + 'lean4', tc_dir / 'src/lean', tc_dir / 'lib/lean',
                  f'https://github.com/leanprover/lean4/blob/{toolchain.split(":")[1]}/src/'))
    return roots


def read_usages(base, repo, rel, usages, local):
    """Single-line usages of constants in one file, as Lean recorded them."""
    ilean = base[2] / rel.replace('.lean', '.ilean')
    if not ilean.exists():
        return False
    lines = (base[1] / rel).read_text().split('\n')
    found = usages[f'{repo}:{rel}'] = []
    data = json.loads(ilean.read_text())
    local[f'{repo}:{rel}'] = {n: r[0] + 1 for n, r in data['decls'].items()}
    for key, ref in data['references'].items():
        ident = json.loads(key).get('c')
        for l0, c0, l1, c1, *_ in (ref['usages'] if ident else ()):
            if l0 == l1 and l0 < len(lines):
                a, b = utf16_to_index(lines[l0], c0), utf16_to_index(lines[l0], c1)
                found.append((l0 + 1, a, b - a, ident['n']))
    return True


def lean_ranges(checkout, groups, names):
    """Declaring module and line of each name, from Lean, importing `groups` in turn."""
    work, mods = OUT.parent / '.names.txt', OUT.parent / '.modules.txt'
    OUT.parent.mkdir(parents=True, exist_ok=True)
    ranges = {}
    for group in groups:
        todo = [n for n in names if n not in ranges]
        work.write_text('\n'.join(todo) + '\n')
        mods.write_text('\n'.join(group) + '\n')
        subprocess.run(['lake', 'env', 'lean', '--run', str(root / 'scripts/LeanDeclRanges.lean'),
                        str(mods), str(work), str(work.with_suffix('.json'))], cwd=checkout, check=True)
        ranges.update(json.loads(work.with_suffix('.json').read_text()))
    for path in (work, mods, work.with_suffix('.json')):
        path.unlink()
    return ranges


def locate(roots, module):
    for key, src, ilean, url in roots:
        if (ilean / (module.replace('.', '/') + '.ilean')).exists():
            return key, module.replace('.', '/') + '.lean'
    return None


def extract_global(checkout, source, page_text, files, targets, urls, texts, previews):
    """References in the GlobalStafford files quoted in index.html, resolved in
    that project's own environment and linked to its own pinned revisions."""
    head = git(checkout, 'rev-parse', 'HEAD').strip()
    if head != source['commit']:
        raise SystemExit(f'GlobalStafford checkout is at {head}, expected {source["commit"]}')
    base_url = f'https://github.com/{source["repo"]}/blob/{head}/'
    roots = checkout_roots(checkout, 'global', base_url, 'global-')
    quoted = sorted(set(re.findall(re.escape(base_url) + r'([^"#]+\.lean)#L', page_text)))
    usages, local = {}, {}
    for rel in quoted:
        if not read_usages(roots[0], 'global', rel, usages, local):
            raise SystemExit(f'GlobalStafford file without .ilean: {rel}')
        texts[f'global:{rel}'] = (checkout / rel).read_text().split('\n')
    names = sorted({u[3] for found in usages.values() for u in found})
    ranges = lean_ranges(checkout, [['GlobalStafford']], names)
    index, first = {}, len(targets)
    for name in names:
        if name in ranges and (owner := locate(roots, ranges[name][0])):
            index[name] = len(targets)
            targets.append([name, owner[0], owner[1], ranges[name][1]])
    for key, found in usages.items():
        files[key] = sorted({(l, c, n, index[t]) for l, c, n, t in found if t in index})
    urls.update({r[0]: r[3] for r in roots if r[3]})
    add_previews(roots, targets, first, previews)
    return [n for n in names if n not in index]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--formal', type=Path, required=True,
                        help='built checkout of the pinned formal commit (lake build)')
    parser.add_argument('--global', dest='global_checkout', type=Path,
                        help='built checkout of the pinned GlobalStafford commit, for its quoted files')
    args = parser.parse_args()
    formal = args.formal.resolve()
    mapping = json.loads((root / 'paper-lean-map.json').read_text())
    sources = mapping['sources']
    head = git(formal, 'rev-parse', 'HEAD').strip()
    if head != sources['formal']['commit']:
        raise SystemExit(f'formal checkout is at {head}, expected {sources["formal"]["commit"]}')
    toolchain = (formal / 'lean-toolchain').read_text().strip()
    roots = checkout_roots(formal, 'formal', None, '')
    if git(formal / '.lake/packages/algebraicAnalysis', 'rev-parse', 'HEAD').strip() != sources['library']['commit']:
        raise SystemExit('AlgebraicAnalysis package differs from the pinned library commit')
    linked = {'formal': git(formal, 'ls-files', '*.lean').split(),
              'library': git(formal / '.lake/packages/algebraicAnalysis', 'ls-files', '*.lean').split()}
    # Library files quoted in index.html from GitHub (Mathlib and the like).
    quoted, texts = {}, {}
    # Only the generator's own source links, not links this tooling added.
    page_text = ' '.join(re.findall(r'<a [^>]*source-link[^>]*>', (root / 'index.html').read_text()))
    for repo, src, ilean, url in roots:
        if url and repo != 'library':
            for rel in sorted(set(re.findall(re.escape(url) + r'([^"#]+\.lean)#L', page_text))):
                quoted.setdefault(repo, []).append(rel)
                texts[f'{repo}:{rel}'] = (src / rel).read_text().split('\n')

    # Pass 1: every single-line usage of a constant, as Lean recorded it.
    usages, local, missing = {}, {}, set()
    for repo, names in [*linked.items(), *quoted.items()]:
        base = next(r for r in roots if r[0] == repo)
        for rel in names:
            if not read_usages(base, repo, rel, usages, local):
                missing.add(f'{repo}:{rel}')

    # Pass 2: Lean itself reports the declaring module and line of each constant.
    names = sorted({u[3] for found in usages.values() for u in found})
    # Every built module, so all referenced names are in scope. The standalone
    # challenge and solution files redefine the challenge names, so each of
    # them is imported on its own for the names still missing.
    built = [k.split(':', 1)[1].removesuffix('.lean').replace('/', '.')
             for k in usages if k.startswith('formal:') and not k.startswith('formal:tests/')]
    ranges = lean_ranges(formal, [[m for m in built if '.' in m]] + [[m] for m in built if '.' not in m], names)
    targets, index = [], {}
    for name in names:
        if name in ranges and (owner := locate(roots, ranges[name][0])):
            index[name] = len(targets)
            targets.append([name, owner[0], owner[1], ranges[name][1]])
    # A name the file declares itself refers to that declaration (the
    # standalone challenge files repeat the challenge definitions).
    def resolve(key, name):
        if name in local[key]:
            if (key, name) not in index:
                repo, rel = key.split(':', 1)
                index[key, name] = len(targets)
                targets.append([name, repo, rel, local[key][name]])
            return index[key, name]
        return index.get(name)
    files = {}
    for key, found in usages.items():
        spans = {(l, c, n, resolve(key, t)) for l, c, n, t in found}
        files[key] = sorted(sp for sp in spans if sp[3] is not None)
    unresolved = [n for n in names if n not in index]
    urls = {r[0]: r[3] for r in roots if r[3]}
    previews = {}
    add_previews(roots, targets, 0, previews)
    if args.global_checkout:
        unresolved += extract_global(args.global_checkout.resolve(), sources['global'], page_text,
                                     files, targets, urls, texts, previews)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(dict(
        schema=1, formal_commit=head, library_commit=sources['library']['commit'], toolchain=toolchain,
        source='Usages from the .ilean files of the built checkout; declaration lines from Lean findDeclarationRanges?. Columns are code points.',
        urls=urls, targets=targets, previews=previews, unresolved=unresolved, files=files, texts=texts),
        ensure_ascii=False,
        separators=(',', ':')) + '\n')

    labels = {'formal': ('sources/formal', sources['formal']),
              'library': ('sources/library', sources['library'])}
    written = 0
    for repo, names in linked.items():
        base_dir, meta = labels[repo]
        src = next(r for r in roots if r[0] == repo)[1]
        for rel in names:
            dest = root / base_dir / (rel + '.html')
            if f'{repo}:{rel}' in files and not dest.exists():
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(page(rel, meta['label'], meta['commit'], (src / rel).read_text()))
                written += 1
    print(f'{sum(map(len, files.values()))} references in {len(files)} files to {len(targets)} '
          f'declarations; {len(unresolved)} without a source line; {len(missing)} files without .ilean; '
          f'{written} new source pages.')


if __name__ == '__main__':
    main()
