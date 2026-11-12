#!/usr/bin/env python3
"""Render definitions.html: how each definition of the paper enters the Lean proof.

definitions.json lists, per printed definition, its Lean form, the definition
the proofs work with and the theorems connecting the two. With --formal PATH
(a built checkout of the pinned formal commit) Lean's dependency graph
(scripts/LeanDag.lean) decides which of these declarations the proofs of
Theorem 1.1 and Corollary 6.3 use, and the result is stored in
verification/definitions/usage.json. Without --formal the page is rendered
from that file. Links and Lean texts come from
verification/lean-references/references.json.
"""
from pathlib import Path
import argparse, html, importlib.util, json, re, subprocess

root = Path(__file__).resolve().parent.parent
SPEC = root / 'definitions.json'
DATA = root / 'verification/definitions/usage.json'
REFS = root / 'verification/lean-references/references.json'
spec = importlib.util.spec_from_file_location('paperdag', root / 'scripts/build-proof-dag.py')
paperdag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paperdag)
esc = html.escape

CLASSES = {
    'direct': ('as printed', 'hyp',
               'The Lean definition is the printed one, and the statements and proofs use it as it stands. '
               'A theorem listed in such a row relates it to a further form that single steps use.'),
    'alias': ('another name', 'dep',
              'The printed name abbreviates a definition of the working modules. Both are the same object '
              'by definition; no theorem is needed.'),
    'library': ('Mathlib', 'std',
                'The printed notion is Mathlib\'s. Where the paper describes it, a Lean theorem states '
                'that description as a property of Mathlib\'s notion.'),
    'equivalent': ('equivalence proved', 'cited',
                   'The printed definition is written out on its own, the proofs work with a different '
                   'definition, and Lean theorems prove that the two agree.'),
    'implied': ('implication proved', 'warn',
                'As before, but Lean proves only the direction the proofs need: the printed condition '
                'implies the one the proofs use.'),
}
STYLE = paperdag.STYLE + '''
.tag{display:inline-block;border:1.5px solid var(--k);background:var(--f);border-radius:3px;
padding:0 .4em;font-size:.78rem;white-space:nowrap}
.use{font-size:.78rem;color:var(--mute)}.use.no{color:var(--warnk)}
td code,li code,p code{font-size:.82rem;overflow-wrap:anywhere}
td ul{margin:0;padding-left:1.1em}td li{margin:.15rem 0}
.defs table{table-layout:fixed;min-width:920px}.defs th:nth-child(1){width:15%}.defs th:nth-child(2){width:11%}
.defs th:nth-child(3),.defs th:nth-child(4){width:20%}
details{margin:.2rem 0}details pre{background:var(--cl);border:1px solid var(--line);border-radius:6px;
padding:.5rem;overflow-x:auto;font-size:.78rem;white-space:pre-wrap}
summary{cursor:pointer}
.layers{display:grid;gap:8px;margin:.8rem 0}
.layer{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--k);border-radius:6px;padding:.5rem .7rem}
.layer b{display:block}.layer span{font-size:.85rem}.down{text-align:center;color:var(--mute);line-height:1}
'''


def names_in(spec_data):
    out = set(spec_data['roots'].values())
    for group in spec_data['groups']:
        for row in group['rows']:
            out.update(row['printed'], row['working'], (b['name'] for b in row['bridges']))
    out.update(s['name'] for s in spec_data['statements'])
    out.update(e['name'] for part in spec_data['geometry'].values() for e in part)
    return out


def extract(formal, spec_data):
    DATA.parent.mkdir(parents=True, exist_ok=True)
    raw_path = DATA.parent / '.raw.json'
    subprocess.run(['lake', 'env', 'lean', '--run', str(root / 'scripts/LeanDag.lean'), str(raw_path)],
                   cwd=formal, check=True)
    raw = json.loads(raw_path.read_text())
    raw_path.unlink()
    g, ext = raw['constants'], raw['externals']

    def cone(start):
        seen, todo = set(), [start]
        while todo:
            c = todo.pop()
            if c in seen or c not in g:
                continue
            seen.add(c)
            todo.extend(g[c]['uses'])
        return seen

    roots = spec_data['roots']
    cones = {key: cone(name) for key, name in roots.items()}
    outside = {key: {e for c in members for e in g[c]['external']} for key, members in cones.items()}
    tracked = names_in(spec_data)
    missing = sorted(n for n in tracked if n not in g and n not in ext)
    if missing:
        raise SystemExit('declarations not in the Lean environment: ' + ', '.join(missing))
    used = {n: sorted(key for key in roots if n in cones[key] or n in outside[key]) for n in sorted(tracked)}
    kinds = {n: g[n]['kind'] if n in g else ext[n][1] for n in sorted(tracked)}
    # The tracked definitions that a statement names directly.
    stated = {s['name']: sorted(d for d in set(g[s['name']]['statement']) if d in tracked and d != s['name'])
              for s in spec_data['statements']}
    geometry = sorted({i['module'] for i in g.values() if i['module'].startswith('Stafford38.Geometry.')})
    by_root = {key: sorted({g[c]['module'] for c in members} & set(geometry)) for key, members in cones.items()}
    library = sorted({ext[e][0] for e in outside['main'] if e in ext and ext[e][0].startswith('AlgebraicAnalysis')})
    head = subprocess.check_output(['git', '-C', str(formal), 'rev-parse', 'HEAD'], text=True).strip()
    DATA.write_text(json.dumps(dict(
        schema=1, formal_commit=head,
        source='Constants used by types and proofs (scripts/LeanDag.lean). "used" lists the roots whose '
               'proof reaches a declaration; "stated" lists the tracked declarations a statement names.',
        roots=roots, used=used, kinds=kinds, stated=stated,
        geometry=dict(modules=len(geometry), main=by_root['main'], original=len(by_root['original']),
                      shared=len(set(by_root['main']) & set(by_root['original']))),
        library_modules=library), indent=1, ensure_ascii=False) + '\n')


def page(spec_data, data):
    refs = json.loads(REFS.read_text())
    if refs['formal_commit'] != data['formal_commit']:
        raise SystemExit('usage.json and references.json are from different formal commits')
    index = {}
    for i, target in enumerate(refs['targets']):
        index.setdefault(target[0], i)
    missing = sorted(n for n in names_in(spec_data) if n not in index or n not in data['used'])
    if missing:
        raise SystemExit('declarations without reference data: ' + ', '.join(missing))

    def short(name):
        for prefix in ('Stafford38.Paper.', 'Stafford38.Geometry.', 'Stafford38.'):
            if name.startswith(prefix):
                return name[len(prefix):]
        return name

    def href(name):
        _, repo, path, line = refs['targets'][index[name]]
        if repo == 'formal':
            return f'./sources/formal/{path}.html#L{line}'
        if repo == 'library':
            return f'./sources/library/{path}.html#L{line}'
        return f'{refs["urls"][repo]}{path}#L{line}'

    def owner(name):
        repo = refs['targets'][index[name]][1]
        return {'formal': 'Stafford38', 'library': 'AlgebraicAnalysis', 'mathlib': 'Mathlib'}.get(repo, repo)

    def link(name):
        return f'<a href="{esc(href(name))}" title="{esc(name)}"><code>{esc(short(name))}</code></a>'

    def text(s):
        return re.sub(r'`([^`]+)`', r'<code>\1</code>', esc(s))

    def usage(name):
        used = data['used'][name]
        if 'main' in used:
            return '<span class="use">used in the proof of Theorem 1.1</span>'
        if 'cyclic' in used or 'stable' in used:
            return '<span class="use">used for Corollary 6.3</span>'
        if 'original' in used:
            return '<span class="use">not used for Theorem 1.1 or Corollary 6.3; the earlier proof of the universal statement uses it</span>'
        return '<span class="use no">not used by a later proof</span>'

    def tag(cls):
        label, colour, _ = CLASSES[cls]
        return f'<span class="tag" style="--f:var(--{colour});--k:var(--{colour}k)">{esc(label)}</span>'

    def names(items):
        return '<br>'.join(link(n) for n in items) or '<span class="mute">—</span>'

    sections, counts = [], {c: 0 for c in CLASSES}
    for group in spec_data['groups']:
        rows = []
        for row in group['rows']:
            counts[row['class']] += 1
            bridges = ''.join(f'<li>{link(b["name"])}: {text(b["says"])}<br>{usage(b["name"])}</li>'
                              for b in row['bridges'])
            rows.append(
                f'<tr><td class="n"><b>{text(row["notion"])}</b><br><span class="mute">{esc(row["paper"])}</span></td>'
                f'<td>{tag(row["class"])}</td><td class="c">{names(row["printed"])}</td>'
                f'<td class="c">{names(row["working"])}</td>'
                f'<td>{text(row["note"])}{"<ul>" + bridges + "</ul>" if bridges else ""}</td></tr>')
        sections.append(
            f'<h3>{esc(group["title"])}</h3><div class="tbl defs"><table><thead><tr><th>Notion</th><th>Relation</th>'
            f'<th>Lean form of the printed definition</th><th>Definition the proofs work with</th>'
            f'<th>How they are connected</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>')

    stated = []
    for s in spec_data['statements']:
        defs = [d for d in data['stated'][s['name']] if data['kinds'][d] != 'theorem']
        stated.append(f'<tr><td>{esc(s["paper"])}</td><td>{link(s["name"])}</td>'
                      f'<td>{", ".join(link(d) for d in defs) or "—"}</td></tr>')

    def preview(name):
        body = refs['previews'][str(index[name])]
        return f'<details><summary>Lean text</summary><pre>{esc(body)}</pre></details>'

    geo = spec_data['geometry']
    core = ''.join(f'<tr><td>{esc(e["paper"])}</td><td>{link(e["name"])}{preview(e["name"])}</td>'
                   f'<td>{text(e["says"])}</td></tr>' for e in geo['core'])
    mathlib_rows = ''.join(f'<tr><td>{link(e["name"])}</td><td>{text(e["says"])}</td><td>{usage(e["name"])}</td></tr>'
                      for e in geo['mathlib'])
    g = data['geometry']
    mathlib = re.search(r'/blob/([0-9a-f]{7})', refs['urls']['mathlib'])[1]
    legend = ''.join(f'<li style="--f:var(--{colour});--k:var(--{colour}k)"><b>{esc(label)}</b>: {esc(meaning)}</li>'
                     for label, colour, meaning in CLASSES.values())
    modules = ', '.join(f'<code>{esc(m.rpartition(".")[2])}</code>' for m in g['main'])
    layers = [
        ('std', 'Mathlib', 'Spectra, zero sets and vanishing ideals, smooth locus, Kähler differentials, '
                           'valuation rings, completions, power and Laurent series, projective space.'),
        ('dep', 'Stafford38.Geometry',
         f'{g["modules"]} modules of this project. They define tangent and conormal spaces, the conormal cone, '
         f'fibre-conical sets and the valuation rings and Laurent expansions of Subsection 5.2, and prove the '
         f'supporting lemmas. '
         f'{len(g["main"])} of them are used by the proof of Theorem 1.1.'),
        ('hyp', 'Stafford38.Paper.Section5',
         'Definitions 5.1 to 5.6 in the printed form, the theorems that identify them with the definitions '
         'above, and Lemmas 5.9 to 5.13 and Theorems 5.7 and 5.8 proved paragraph by paragraph.'),
        ('goal', 'Section 6', 'Theorem 5.8 is applied to W = V_K(Ann gr Q_K) and shows W empty. Then the module '
                              'Q = A_n/(d̃A_n + x₁^N d̃A_n) is zero, which is the identity of Theorem 1.1.'),
    ]
    stack = '<div class="down">↓</div>'.join(
        f'<div class="layer" style="--k:var(--{colour}k)"><b>{esc(name)}</b><span>{esc(what)}</span></div>'
        for colour, name, what in layers)
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stafford 3.8 definitions</title>
<meta name="description" content="How each definition of the Stafford Conjecture 3.8 paper enters the Lean proof.">
<style>{STYLE}</style>
</head><body>
<main>
<p class="mute"><a href="index.html">← Proof comparison</a> · <a href="proof-dag.html">Paper proof graph</a> ·
<a href="lean-dag.html">Lean proof graph</a></p>
<h1>Definitions: printed form and form used by the proofs</h1>
<p>The Lean modules <code>Stafford38.Paper</code> state the definitions of the paper as printed. Some of
these are the definitions the Lean proofs work with. Others are stated separately and connected, by a Lean
theorem, to a different definition that the proofs use. That definition lives in the working modules, the
other modules of the project. This page lists which case applies to each
notion: {counts['direct']} are used as printed, {counts['alias']} are other names, {counts['library']} are
Mathlib's, for {counts['equivalent']} an equivalence is proved and for {counts['implied']} an implication.</p>
<p>Notation: k is the ground field of characteristic zero, K an algebraically closed field containing it, over
which the geometry of Section 5 takes place. A point is a tuple of coordinates in K. The stand-alone statements
are the versions of Theorem 1.1 and Corollary 6.3 written with Mathlib alone, against which the proofs are
checked independently (the cards "Challenge comparison" of the <a href="index.html">proof comparison</a>). The
Lean sources are those of commit {data['formal_commit'][:7]} of the formal repository, with Mathlib at commit
{mathlib}.</p>
<ul class="legend" style="display:block">{legend}</ul>
<p>Under each connecting theorem the page says whether a later proof uses it. Lean stores, for every proof,
the declarations it refers to; following these references from Theorem 1.1
(<code>{esc(data['roots']['main'])}</code>) and from Corollary 6.3 gives everything their proofs depend on. A
connecting theorem outside this set is still proved; it documents that the printed form agrees, and no later
argument rests on it.</p>
<h2 id="definitions">Definitions by section</h2>
{"".join(sections)}
<h2 id="statements">Which definitions the main statements name</h2>
<p>The definitions that occur directly in the Lean statement of each result. Theorem 5.8, for example, is stated
with the fibre-conical and involutive conditions of the proofs, which the table above connects to Definitions 5.6
and 2.10.</p>
<div class="tbl"><table><thead><tr><th>Paper</th><th>Lean statement</th><th>Definitions named in it</th></tr></thead>
<tbody>{"".join(stated)}</tbody></table></div>
<h2 id="geometry">Geometry: where the definitions of Section 5 live</h2>
<p>Section 5 is the geometric part of the proof. Its Lean definitions sit in three layers. General notions come
from Mathlib. The notions specific to this proof are defined in the project's own geometry modules,
<code>Stafford38.Geometry</code>. The modules <code>Stafford38.Paper.Section5</code> restate them as printed and
prove the statements of the paper. The separate library AlgebraicAnalysis, on which the project also depends,
contributes Ore extensions and filtered modules to Sections 3 and 4 ({len(data['library_modules'])} of its
modules are used by the proof of Theorem 1.1) and no geometry.</p>
<div class="layers">{stack}</div>
<h3>Core geometric definitions</h3>
<p>All are sets or subspaces given by explicit conditions on points y ∈ K^n and covectors ξ ∈ (K^n)*. An
irreducible closed set Y enters through its prime ideal 𝔭 = I(Y), a point of Spec K[x]. No schemes or sheaves
are involved beyond Mathlib's prime spectrum.</p>
<div class="tbl"><table><thead><tr><th>Paper</th><th>Lean definition</th><th>Meaning</th></tr></thead>
<tbody>{core}</tbody></table></div>
<h3>Mathlib notions used by the geometry</h3>
<div class="tbl"><table><thead><tr><th>Mathlib</th><th>Role in Section 5</th><th></th></tr></thead>
<tbody>{mathlib_rows}</tbody></table></div>
<h3>Geometry modules behind Theorem 1.1</h3>
<p>The repository holds two proofs of the identity 1 = dR + FdS. The proof of Theorem 1.1 follows the paper and
uses {len(g['main'])} of the {g['modules']} geometry modules. An earlier proof of the same identity
(<code>{esc(data['roots']['original'])}</code>) takes a different route
through the geometry and uses {g['original']} modules; {g['shared']} serve both, and
{g['modules'] - len(g['main']) - g['original'] + g['shared']} serve neither. The earlier proof is not needed to
read the paper. The statements of Section 5 themselves, Lemmas 5.9 to 5.13 and Theorems 5.7 and 5.8, are in
<code>Stafford38.Paper.Section5</code>.</p>
<details><summary>The {len(g['main'])} geometry modules used by the proof that follows the paper (internal names)</summary><p>{modules}</p></details>
<p class="mute">Generated by <code>scripts/build-definitions.py</code> from <code>definitions.json</code>,
<code>verification/definitions/usage.json</code> and <code>verification/lean-references/references.json</code>.
The page is a reading aid for the checked proof.</p>
</main>
</body></html>
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--formal', type=Path, help='built checkout of the pinned formal commit')
    args = parser.parse_args()
    spec_data = json.loads(SPEC.read_text())
    if args.formal:
        extract(args.formal.resolve(), spec_data)
    data = json.loads(DATA.read_text())
    (root / 'definitions.html').write_text(page(spec_data, data))
    paperdag.refresh_checksums()
    rows = sum(len(group['rows']) for group in spec_data['groups'])
    print(f'Wrote definitions.html: {rows} notions, {len(data["used"])} declarations checked.')
