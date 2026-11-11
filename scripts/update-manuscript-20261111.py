#!/usr/bin/env python3
"""Map the reader to the November 11 manuscript without editing the paper.

Since the November 2 version the authors corrected the displayed order symbol
in the proof of Proposition 3.2, removed the formal-comparison notes and the
last AI comment, and fixed wording; every Lean reference of the manuscript now
names the declaration of its statement in Stafford38.Paper at the pinned formal
commit. No statement is added, removed or renumbered, so every card keeps its
id, label, number and Lean mapping; excerpt ranges are recomputed for the new
source. The earlier update-manuscript*.py scripts are kept unchanged.

The base map is read from a committed supplementary revision (default HEAD),
so the migration can be rerun after its own commit with --base-rev.
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
RECEIPT = ROOT / 'verification/manuscript-20261111'
VERSION = '0.3.0'
UPDATED = '2026-11-11'
_spec = importlib.util.spec_from_file_location('previous', ROOT / 'scripts/update-manuscript-20261102.py')
previous = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(previous)
git, active_tex = previous.git, previous.active_tex


def template_anchors(raw):
    """The Springer Nature template's front and back matter, rewritten to the amsart anchors of the range rules.

    Only the copy used for computing line ranges is rewritten; every replacement stays on its line.
    """
    start = raw.find('\\abstract{')
    if start >= 0:
        depth, end = 0, start + len('\\abstract')
        for end in range(end, len(raw)):
            depth += {'{': 1, '}': -1}.get(raw[end], 0)
            if depth == 0:
                break
        raw = raw[:start] + '\\begin{abstract}' + raw[start + len('\\abstract{'):end] + '\\end{abstract}' + raw[end + 1:]
    return (raw.replace('\\backmatter', '\\bibliographystyle{}')
               .replace('\\begin{appendices}', '\\begin{appendix}')
               .replace('\\end{appendices}', '\\end{appendix}'))


def card_ranges(raw, items):
    result = previous.card_ranges(template_anchors(raw), items)
    if '\\abstract{%' in raw:
        # The template abstract opens and closes on lines of their own; the card shows only its text.
        first, last = result[0]['abstract']
        result[0]['abstract'] = [first + 1, last - 1]
    return result

PINNED = 'the Lean sources are pinned to formal commit 1029fdb, which passes the repository verifier'
RESOLVED = {
    'MS28-TYPO-01': 'fixed in the November 11 manuscript',
    'MS28-FIELD-01': 'fixed in the November 11 manuscript',
    'MS21-DEF-01': 'fixed in the November 11 manuscript',
    'MS28-REF-01': 'fixed in the November 11 manuscript: the reference is dropped',
    'challenge-main-freeze': 'done: ' + PINNED,
    'challenge-fixed-source-freeze': 'done: ' + PINNED,
}
TEXTS = {
    'abstract': (
        'The red proposal now states n>=1 for the fixed-source coordinate strengthening. The universal identity '
        'also holds at rank zero. Compare both proved endpoints and their fully expanded challenge definitions; '
        'author acceptance remains pending.',
        'The abstract states the identity and the cyclicity of torsion modules; it does not mention the '
        'strengthening of Theorem 1.1 with F a power of a linear coordinate, which needs n>=1. The universal '
        'identity also holds at rank zero. Compare both proved endpoints and their fully expanded challenge '
        'definitions.'),
    'generalization-filtered': (
        'The paper gives no printed proof; the manuscript marks the citation as a placeholder (AI comment FV-03).',
        'The paper gives no printed proof and cites the result as in preparation.'),
    'outlook': (' FV-03 marks the citation of generalization (b) as a placeholder.', ''),
    'further-work': (
        'The identity in every right Ore localization is no longer listed, although the paragraph’s Lean '
        'reference still cites it (MS28-REF-01).',
        'The identity in every right Ore localization is not listed.'),
}


def formal_pin(ai_review):
    """The formal commit that the manuscript's Lean links point to."""
    return re.search(r'stafford38-formal/blob/([0-9a-f]{40})', ai_review)[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper', type=Path, required=True,
                        help='Clean checkout of the paper repository (read only).')
    parser.add_argument('--commit', required=True)
    parser.add_argument('--base-rev', default='HEAD',
                        help='Supplementary revision whose map and manifest are migrated.')
    parser.add_argument('--paper-build', type=Path,
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
        raise SystemExit('Base revision is already migrated; pass --base-rev of the November 2 map')
    items = mapping['items']
    by_id = {i['id']: i for i in items}
    # The range rules must reproduce the base map on its own source.
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
    # ------------------------------------------------- findings and texts ----
    for item in items:
        fixed = [i for i in item['issues'] if i['id'] in RESOLVED]
        if fixed:
            item['issues'] = [i for i in item['issues'] if i['id'] not in RESOLVED]
            item['historical_issues'] = item.get('historical_issues', []) + [dict(i, status=RESOLVED[i['id']]) for i in fixed]
            item['comparison_updated_on'] = UPDATED
    for identifier, (old_text, new_text) in TEXTS.items():
        item = by_id[identifier]
        if item['correspondence'].count(old_text) != 1:
            if old_text and new_text and new_text in item['correspondence']:
                continue
            if not new_text and old_text not in item['correspondence']:
                continue
            raise ValueError(f'Card text of {identifier} changed; update TEXTS')
        item['correspondence'] = item['correspondence'].replace(old_text, new_text)
        item['comparison_updated_on'] = UPDATED
    # ------------------------------------------------- source and texts ----
    source = dict(old_source, commit=commit, origin_commit=commit,
                  sha256=hashlib.sha256(raw.encode()).hexdigest(), label='Paper (November 11 version)',
                  note='November 11 version, preserved verbatim.')
    snapshot_files = {}
    snapshot_base = ROOT / 'sources/paper/raw'
    snapshot_base.mkdir(parents=True, exist_ok=True)
    for file in ['human_readable_main.tex', 'references.bib', 'ai_review.tex', 'sn-jnl.cls', 'sn-mathphys-num.bst']:
        content = subprocess.check_output(['git', '-C', str(paper), 'show', f'{commit}:{file}'])
        (snapshot_base / file).write_bytes(content)
        snapshot_files[file] = hashlib.sha256(content).hexdigest()
    source['snapshot'] = dict(base='sources/paper/raw', files=snapshot_files)
    open_findings = sorted(i['id'] for item in items for i in item['issues'] if i['id'].startswith('MS'))
    mapping['version'] = VERSION
    mapping['subtitle'] = 'November 11 manuscript · paper and Lean proof comparison'
    if open_findings:
        raise ValueError(f'Open manuscript findings remain: {open_findings}')
    mapping['reader_notice'] = 'Manuscript updated 11 November 2026. No review finding is open.'
    mapping['sources']['paper'] = source
    clean = active_tex(raw)
    line_at = lambda pos: clean.count('\n', 0, pos) + 1
    mapping['aicomments'] = [dict(id=m[1], line=line_at(m.start()), verdict='author review pending',
        note='Active annotation in the updated manuscript; no author acceptance is inferred.')
        for m in re.finditer(r'\\AIcomment\{([^{}]+)\}', clean)]
    mapping['provenance'] = mapping['provenance'].replace('the November 2 frozen version', 'the November 11 version')
    mapping['comparison_scope'] = (
        'The November 11 manuscript. Lean sources are pinned to formal commit 1029fdb, '
        'which states every numbered statement of Sections 2–6 in Stafford38.Paper; it passes the repository '
        'verifier. The Lean references of the manuscript name these declarations at the same commit.')
    mapping['overview'] = (
        'Compare the November 11 manuscript with the pinned Lean results. Every theorem-like statement '
        'has a card. In Subsection 5.2 Theorem 5.7 and Lemmas 5.9–5.13 each have their own Lean theorem, and '
        'Theorem 5.7 is proved in Lean along the printed route; the earlier chart-based proof is kept as an '
        'alternative. Matching conclusions elsewhere do not by themselves certify a printed proof step by step.')
    mapping['candidate']['status'] = 'November 11 manuscript refresh'
    mapping['manuscript_sources'] = {'formal': {'commit': formal_pin(git(paper, 'show', f'{commit}:ai_review.tex'))}}
    manifest['manuscript_sources'] = mapping['manuscript_sources']
    mapping['candidate']['manuscript'] = source
    manifest['version'] = mapping['version']
    manifest['sources'] = mapping['sources']
    manifest['review'].update(claims=len(items), scope=mapping['comparison_scope'],
        statement_relations=dict(collections.Counter(i['statement_relation'] for i in items)),
        proof_routes=dict(collections.Counter(i['route_relation'] for i in items)))
    manifest['status'] = 'manuscript-update-in-progress'
    manifest['checks'] = dict(status='pending', receipt='verification/manuscript-20261111/verification.json',
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
        names = [r.get('name') for r in i['lean']]
    if git(paper, 'status', '--porcelain=v1') != before:
        raise SystemExit('Paper worktree changed during migration')
    history = dict(base_supplementary_revision=base_rev, previous_paper=old_source, current_paper=source,
                   renamed_labels={}, deleted_labels=[], renumbered_statements={},
                   removed_cards=[], added_cards=[], moved_ranges=moved,
                   remapped_cards=[], active_statements=len(statements), current_cards=len(items),
                   open_findings=open_findings, expected_unresolved_refs=[],
                   expected_unresolved_citations=[],
                   paper_worktree_status_before=before,
                   note='The paper repository is read-only throughout this migration.')
    RECEIPT.mkdir(parents=True, exist_ok=True)
    if args.paper_build:
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
    else:
        manifest['manuscript_pdfs']['current_paper_commit'] = commit
        manifest['manuscript_pdfs']['paper_pdf_status'] = 'rebuild-required'
    (RECEIPT / 'migration.json').write_text(json.dumps(history, indent=2, ensure_ascii=False) + '\n')
    for name, value in [('paper-lean-map.json', mapping), ('manifest.json', manifest)]:
        (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    (ROOT / 'version.json').write_text(json.dumps(version, indent=2) + '\n')
    print(f'Pinned manuscript {commit[:12]}; {len(items)} cards, {len(moved)} ranges moved, '
          f'{len(statements)} active statements; '
          f'{len(open_findings)} open findings. Paper unchanged.')


if __name__ == '__main__':
    main()
