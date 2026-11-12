#!/usr/bin/env python3
"""Drop technicalities from the Section 2 and 4 cards that do not bear on the printed statements.

Lemmas 4.1-4.9 were labelled "Lean stronger" only because Lean also allows N = 0 (excluded by the paper
throughout) or any ground field, and Definition 2.3 "equivalent" only because Lean indexes filtrations by
N and defines the filtration degree at 0. Both cases are now "exact" and the remarks are removed.
The manuscript and the Lean pins are unchanged. Run rebuild.py afterwards.
"""
from pathlib import Path
import argparse, collections, json, subprocess

ROOT = Path(__file__).resolve().parent.parent
RECEIPT = ROOT / 'verification/labels-20261112'
VERSION = '0.3.2'
UPDATED = '2026-11-12'
EXACT = ['lem:euler', 'lem:euler-residue', 'prop:x-surjective', 'lem:tangential-finiteness', 'lem:page-inequality',
         'def:filtration']
REMOVE = {
    'lem:euler': ['Lean states it for every field k (the characteristic is not used); '],
    'lem:euler-residue': [' Lean does not need N ≥ 1 (for N = 0, (3.1) is d̃ = 1).'],
    'prop:x-surjective': [' Lean does not need N ≥ 1 (for N = 0, (3.1) is d̃ = 1).'],
    'lem:tangential-finiteness': [' Lean does not need N ≥ 1 (for N = 0, (3.1) is d̃ = 1).'],
    'lem:page-inequality': [' Lean does not need N ≥ 1 (for N = 0, (3.1) is d̃ = 1).'],
}


def git(*args):
    return subprocess.check_output(['git', '-C', str(ROOT), *args], text=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-rev', default='HEAD')
    args = parser.parse_args()
    base = git('rev-parse', args.base_rev).strip()
    mapping = json.loads(git('show', f'{base}:paper-lean-map.json'))
    manifest = json.loads(git('show', f'{base}:manifest.json'))
    version = json.loads(git('show', f'{base}:version.json'))
    previous = json.loads(git('show', f'{base}:verification/manuscript-20261112/migration.json'))
    by_id = {i['id']: i for i in mapping['items']}
    for identifier in EXACT:
        by_id[identifier]['statement_relation'] = 'exact'
        by_id[identifier]['comparison_updated_on'] = UPDATED
    for identifier, texts in REMOVE.items():
        for text in texts:
            if by_id[identifier]['correspondence'].count(text) != 1:
                raise ValueError(f'correspondence of {identifier} changed; update REMOVE')
            by_id[identifier]['correspondence'] = by_id[identifier]['correspondence'].replace(text, '')
    mapping['version'] = manifest['version'] = VERSION
    manifest['review']['statement_relations'] = dict(collections.Counter(i['statement_relation'] for i in mapping['items']))
    manifest['checks'] = dict(status='pending', receipt='verification/labels-20261112/verification.json',
                              note='Historical checks remain in their original receipts.')
    version.update(version=VERSION)
    history = dict(previous, base_supplementary_revision=base, previous_paper=previous['current_paper'],
                   moved_ranges={}, corrected_texts=sorted(f'{i}.statement_relation' for i in EXACT)
                   + sorted(f'{i}.correspondence' for i in REMOVE),
                   note='Labels and card texts only; the manuscript and the Lean pins are unchanged.')
    RECEIPT.mkdir(parents=True, exist_ok=True)
    (RECEIPT / 'migration.json').write_text(json.dumps(history, indent=2, ensure_ascii=False) + '\n')
    for name, value in [('paper-lean-map.json', mapping), ('manifest.json', manifest)]:
        (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    (ROOT / 'version.json').write_text(json.dumps(version, indent=2) + '\n')
    print(f'{len(EXACT)} labels set to exact, {sum(map(len, REMOVE.values()))} remarks removed.')


if __name__ == '__main__':
    main()
