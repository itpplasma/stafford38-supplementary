#!/usr/bin/env python3
"""Map the reader to the November 12 manuscript and correct outdated card texts.

Since the November 11 version the authors removed the formal-comparison notes
and the sentence on differing routes, cited formal v1.4.0 and supplementary
v0.3.0, added acknowledgements and contact data and fixed typos. No statement
is added, removed or renumbered. Card texts that described the reader before
formal v1.4.0 (a Corollary 6.3 without Lean counterpart, Lean routes that
differ from the printed proofs) are corrected, and the proof map opens the
reader. The earlier update-manuscript*.py scripts are kept unchanged.

The base map is read from a committed supplementary revision (default HEAD).
Run rebuild.py afterwards to regenerate the reader.
"""
from pathlib import Path
import argparse
import collections
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
RECEIPT = ROOT / 'verification/manuscript-20261112'
VERSION = '0.3.1'
UPDATED = '2026-11-12'
_spec = importlib.util.spec_from_file_location('previous', ROOT / 'scripts/update-manuscript-20261111.py')
previous = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(previous)
git, active_tex, card_ranges, formal_pin = previous.git, previous.active_tex, previous.card_ranges, previous.formal_pin

# (old, new) replacements in card fields; each old text must occur exactly once.
TEXTS = {
    ('formal-verification', 'correspondence'): (
        ', the text saying where the two routes differ.', '.'),
    ('abstract', 'correspondence'): (
        'The abstract states the identity and the cyclicity of torsion modules;',
        'The abstract states the identity and the cyclicity of torsion modules, proved as '
        'Stafford38.Paper.theorem_1_1 and Stafford38.Paper.corollary_6_3;'),
    ('intro-proof-sketch', 'route'): (
        'similar: common quotient-vanishing architecture, with Lean making the same-witness geometric '
        'construction and field descent explicit.',
        'similar: the same quotient-vanishing route; Stafford38.Paper proves each step of Sections 3–6 as printed.'),
    ('appendix-left-handed', 'correspondence'): (
        'The paper cites the formal-adjoint corollary directly.',
        'The paper states this consequence without a printed proof.'),
    ('appendix-localized-differential', 'correspondence'): (
        'The paper cites the unconditional localization theorem; its specializations include principal opens, '
        'Laurent-polynomial coefficients, and the fraction field.',
        'The paper states this consequence without a printed proof, including principal opens, '
        'Laurent-polynomial coefficients and the fraction field.'),
    ('appendix-evolutionary', 'correspondence'): (
        'The cited theorem supplies the stated evolutionary extension.',
        'The paper states this consequence without a printed proof.'),
    ('thm:asymptotic-conormal', 'correspondence'): (
        'The terminal theorem GeneralAsymptoticConormal', "The earlier route's GeneralAsymptoticConormal"),
    ('thm:asymptotic-conormal-proof', 'correspondence'): (
        'The terminal theorem GeneralAsymptoticConormal', "The earlier route's GeneralAsymptoticConormal"),
}
# Since formal v1.4.0 these labels no longer hold: Section 1.2 and the abstract claim only what is proved,
# Section 7 gives its consequences without printed proofs, and the Lean localization statement quantifies
# over every localization of k[x_1, ..., x_n], as printed.
FIELDS = {
    ('cyclicity', 'graph_sub'): 'cyclic modules',
    ('formal-verification', 'statement_relation'): 'exact',
    ('abstract', 'statement_relation'): 'exact',
    ('abstract', 'lean'): [
        {'file': 'Stafford38/Paper/Main.lean', 'name': 'Stafford38.Paper.theorem_1_1', 'repo': 'formal', 'role': 'statement'},
        {'file': 'Stafford38/Paper/Main.lean', 'name': 'Stafford38.Paper.corollary_6_3', 'repo': 'formal', 'role': 'statement'},
    ],
    ('appendix-left-handed', 'route_relation'): 'lean-only',
    ('appendix-localized-differential', 'route_relation'): 'lean-only',
    ('appendix-localized-differential', 'statement_relation'): 'exact',
    ('appendix-evolutionary', 'route_relation'): 'lean-only',
}
GRAPH_INTRO = ('Dependencies between the statements of the paper. Click a statement to open its card; the '
               'colour gives how its Lean statement relates to the printed one.')
GRAPH_LINKS = [
    {'label': 'Graph of every printed proof', 'href': 'proof-dag.html'},
    {'label': 'Lean proof graph', 'href': 'lean-dag.html'},
    {'label': 'Definitions', 'href': 'definitions.html'},
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper', type=Path, required=True,
                        help='Clean checkout of the paper repository (read only).')
    parser.add_argument('--commit', required=True)
    parser.add_argument('--base-rev', default='HEAD',
                        help='Supplementary revision whose map and manifest are migrated.')
    parser.add_argument('--generator-commit', required=True)
    parser.add_argument('--generator-bundle', required=True)
    parser.add_argument('--paper-build', type=Path, required=True,
                        help='Isolated build directory with human_readable_main.pdf and .log of this commit.')
    args = parser.parse_args()
    paper = args.paper.resolve()
    before = git(paper, 'status', '--porcelain=v1')
    commit = git(paper, 'rev-parse', args.commit).strip()
    base_rev = git(ROOT, 'rev-parse', args.base_rev).strip()
    mapping = json.loads(git(ROOT, 'show', f'{base_rev}:paper-lean-map.json'))
    manifest = json.loads(git(ROOT, 'show', f'{base_rev}:manifest.json'))
    version = json.loads(git(ROOT, 'show', f'{base_rev}:version.json'))
    old_source = mapping['sources']['paper']
    if old_source['commit'] == commit:
        raise SystemExit('Base revision is already migrated; pass --base-rev of the November 11 map')
    items = mapping['items']
    by_id = {i['id']: i for i in items}
    old_raw = git(paper, 'show', f"{old_source['commit']}:human_readable_main.tex")
    old_ranges, _, old_numbered, _, _ = card_ranges(old_raw, items)
    drift = {i['id']: (i['tex_lines'], old_ranges[i['id']]) for i in items if i['tex_lines'] != old_ranges[i['id']]}
    if drift:
        raise ValueError(f'Range rules do not reproduce the base map: {drift}')
    raw = git(paper, 'show', f'{commit}:human_readable_main.tex')
    ranges, statements, numbered, labels, lines = card_ranges(raw, items)
    if numbered != old_numbered:
        raise ValueError('Statements were added, removed or renumbered; this migration does not handle that')
    moved = {}
    for item in items:
        if item['tex_lines'] != ranges[item['id']]:
            moved[item['id']] = [item['tex_lines'], ranges[item['id']]]
        item['tex_lines'] = ranges[item['id']]
    # ------------------------------------------------------ card texts ----
    for (identifier, field), (old_text, new_text) in TEXTS.items():
        item = by_id[identifier]
        if item[field].count(old_text) != 1:
            raise ValueError(f'{field} of {identifier} changed; update TEXTS')
        item[field] = item[field].replace(old_text, new_text)
        item['comparison_updated_on'] = UPDATED
    for (identifier, field), value in FIELDS.items():
        by_id[identifier][field] = value
        by_id[identifier]['comparison_updated_on'] = UPDATED
    # ------------------------------------------------- source and texts ----
    source = dict(old_source, commit=commit, origin_commit=commit,
                  sha256=hashlib.sha256(raw.encode()).hexdigest(), label='Paper (November 12 version)',
                  note='November 12 version, preserved verbatim.')
    snapshot_files = {}
    snapshot_base = ROOT / 'sources/paper/raw'
    for file in ['human_readable_main.tex', 'references.bib', 'ai_review.tex', 'sn-jnl.cls', 'sn-mathphys-num.bst']:
        content = subprocess.check_output(['git', '-C', str(paper), 'show', f'{commit}:{file}'])
        (snapshot_base / file).write_bytes(content)
        snapshot_files[file] = hashlib.sha256(content).hexdigest()
    source['snapshot'] = dict(base='sources/paper/raw', files=snapshot_files)
    open_findings = sorted(i['id'] for item in items for i in item['issues'] if i['id'].startswith('MS'))
    if open_findings:
        raise ValueError(f'Open manuscript findings remain: {open_findings}')
    mapping['version'] = VERSION
    mapping['subtitle'] = 'November 12 manuscript · paper and Lean proof comparison'
    mapping['reader_notice'] = 'Manuscript updated 12 November 2026. No review finding is open.'
    mapping['graph_intro'] = GRAPH_INTRO
    mapping['graph_links'] = GRAPH_LINKS
    mapping['sources']['paper'] = source
    clean = active_tex(raw)
    line_at = lambda pos: clean.count('\n', 0, pos) + 1
    mapping['aicomments'] = [dict(id=m[1], line=line_at(m.start()), verdict='author review pending',
        note='Active annotation in the updated manuscript; no author acceptance is inferred.')
        for m in re.finditer(r'\\AIcomment\{([^{}]+)\}', clean)]
    mapping['provenance'] = (mapping['provenance'].replace('the November 11 version', 'the November 12 version')
                             .replace(' Comparison labels do not certify a revised printed proof.', ''))
    # The list described where the earlier formal route departs from the paper; the paper route has no such places.
    mapping['lean_only'] = []
    mapping.pop('lean_only_intro', None)
    mapping['candidate']['formal'] = dict(repo='itpplasma/stafford38-formal', commit=mapping['sources']['formal']['commit'],
                                          release='v1.4.0', doi='10.5281/zenodo.24140371')
    mapping['candidate']['note'] = ('Formal v1.4.0 holds the Lean sources of the pinned commit. Johanna Moser reviewed the '
                                    'paper and Maximilian Philipp the correspondence of paper and Lean statements.')
    mapping['comparison_scope'] = (
        'The November 12 manuscript. Lean sources are pinned to formal commit 1029fdb (release v1.4.0), '
        'which states every numbered statement of Sections 2–6 in Stafford38.Paper; it passes the repository '
        'verifier. The Lean references of the manuscript name these declarations at the same commit.')
    mapping['overview'] = (
        'Compare the November 12 manuscript with the pinned Lean results. Every theorem-like statement '
        'has a card. Every numbered statement of Sections 2–6 has its own Lean declaration, and each printed '
        'proof is proved in Lean along the printed argument, paragraph by paragraph. Earlier formal proofs of '
        'the same results are kept as alternatives.')
    mapping['candidate']['status'] = 'November 12 manuscript refresh'
    mapping['manuscript_sources'] = {'formal': {'commit': formal_pin(git(paper, 'show', f'{commit}:ai_review.tex'))}}
    manifest['manuscript_sources'] = mapping['manuscript_sources']
    mapping['candidate']['manuscript'] = source
    manifest['version'] = mapping['version']
    manifest['sources'] = mapping['sources']
    manifest['generator'] = dict(manifest['generator'], commit=args.generator_commit,
                                 version='manuscript-20261112', bundle=args.generator_bundle)
    manifest['review'].update(claims=len(items), scope=mapping['comparison_scope'],
        statement_relations=dict(collections.Counter(i['statement_relation'] for i in items)),
        proof_routes=dict(collections.Counter(i['route_relation'] for i in items)))
    manifest['status'] = 'manuscript-update-in-progress'
    manifest['checks'] = dict(status='pending', receipt='verification/manuscript-20261112/verification.json',
        note='Historical checks remain in their original receipts; they do not verify the updated manuscript build.')
    version.update(version=VERSION, paper=commit)
    # ------------------------------------------------------- validation ----
    for label in (s[1] for s in statements):
        if not any(i.get('label') == label for i in items):
            raise ValueError(f'Unmapped active statement {label}')
    for i in items:
        a, b = i['tex_lines']
        if not 1 <= a <= b <= len(lines):
            raise ValueError(f'Invalid range for {i["id"]}: {a}-{b}')
        if i.get('label') and not a <= labels[i['label']] <= b:
            raise ValueError(f'Label {i["label"]} outside range of {i["id"]}')
        if any(d not in by_id for d in i['depends_on']):
            raise ValueError(f'Unknown dependency of {i["id"]}: {i["depends_on"]}')
    if git(paper, 'status', '--porcelain=v1') != before:
        raise SystemExit('Paper worktree changed during migration')
    history = dict(base_supplementary_revision=base_rev, previous_paper=old_source, current_paper=source,
                   renamed_labels={}, deleted_labels=[], renumbered_statements={},
                   removed_cards=[], added_cards=[], moved_ranges=moved,
                   corrected_texts=sorted(f'{i}.{f}' for i, f in [*TEXTS, *FIELDS]),
                   active_statements=len(statements), current_cards=len(items),
                   open_findings=open_findings, expected_unresolved_refs=[], expected_unresolved_citations=[],
                   paper_worktree_status_before=before,
                   note='The paper repository is read-only throughout this migration.')
    RECEIPT.mkdir(parents=True, exist_ok=True)
    build = args.paper_build.resolve()
    for name, content in snapshot_files.items():
        assert hashlib.sha256((build / name).read_bytes()).hexdigest() == content, name
    log = (build / 'human_readable_main.log').read_text()
    assert 'Fatal error' not in log
    assert not re.findall(r"LaTeX Warning: (?:Reference|Citation) `", log)
    pdf = (build / 'human_readable_main.pdf').read_bytes()
    assert pdf.startswith(b'%PDF-')
    (ROOT / 'human_readable_main.pdf').write_bytes(pdf)
    shutil.copyfile(build / 'human_readable_main.log', RECEIPT / 'paper-build.log')
    manifest['manuscript_pdfs'] = dict(paper=dict(
        sha256=hashlib.sha256(pdf).hexdigest(), source_commit=commit,
        build='latexmk -pdf -interaction=nonstopmode -halt-on-error human_readable_main.tex',
        isolated_checkout=True, unresolved_references=[]))
    (RECEIPT / 'migration.json').write_text(json.dumps(history, indent=2, ensure_ascii=False) + '\n')
    for name, value in [('paper-lean-map.json', mapping), ('manifest.json', manifest)]:
        (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    (ROOT / 'version.json').write_text(json.dumps(version, indent=2) + '\n')
    print(f'Pinned manuscript {commit[:12]}; {len(items)} cards, {len(moved)} ranges moved, '
          f'{len(statements)} active statements. Paper unchanged.')


if __name__ == '__main__':
    main()
