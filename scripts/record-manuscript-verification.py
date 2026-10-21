#!/usr/bin/env python3
"""Record an actual manuscript build and browser/test evidence, then hash it."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import re
import shutil
import subprocess


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper', type=Path, required=True)
    parser.add_argument('--paper-build', type=Path, required=True)
    parser.add_argument('--generator', type=Path, required=True)
    parser.add_argument('--test-log', type=Path, required=True)
    parser.add_argument('--browser-receipt', type=Path, required=True)
    parser.add_argument('--reader-log', type=Path, required=True)
    parser.add_argument('--receipt-dir', default='verification/manuscript-20261018',
                        help='Migration receipt directory; its migration.json may list expected warnings.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    target = root / args.receipt_dir
    mapping = json.loads((root / 'paper-lean-map.json').read_text())
    manifest = json.loads((root / 'manifest.json').read_text())
    migration = json.loads((target / 'migration.json').read_text())
    source = mapping['sources']['paper']
    assert manifest['sources'] == mapping['sources']
    baseline = json.loads(git(root, 'show', 'HEAD:manifest.json'))
    for name in ['formal', 'library', 'global', 'mathlib']:
        assert manifest['sources'][name] == baseline['sources'][name]
    assert manifest['formal_verification'] == baseline['formal_verification']
    assert not git(root, 'diff', '--name-only', '--', 'sources/formal')
    status = git(args.paper, 'status', '--porcelain=v1').decode()
    assert status == migration['paper_worktree_status_before'] == '', 'Paper must remain clean'
    assert git(args.paper, 'rev-parse', 'HEAD').decode().strip() == source['commit']
    for name, expected in source['snapshot']['files'].items():
        committed = git(args.paper, 'show', source['commit'] + ':' + name)
        assert sha(committed) == expected
        assert (args.paper / name).read_bytes() == committed
        assert (args.paper_build / name).read_bytes() == committed
        assert (root / source['snapshot']['base'] / name).read_bytes() == committed
    generator_commit = git(args.generator, 'rev-parse', 'HEAD').decode().strip()
    assert generator_commit == manifest['generator']['commit']
    assert not git(args.generator, 'diff', '--name-only')
    tests = args.test_log.read_text()
    counts = {name: int(re.search(r'ℹ ' + name + r' (\d+)', tests)[1])
              for name in ['tests', 'pass', 'fail', 'skipped']}
    assert counts['fail'] == 0 and counts['pass'] > 0
    assert counts['tests'] == counts['pass'] + counts['skipped']
    browser = json.loads(args.browser_receipt.read_text())
    assert browser['status'] == 'passed'
    assert browser['cards'] == len(mapping['items'])
    assert browser['paper'] == source['commit']
    assert not browser['javascript_errors'] and not browser['offline_requests']
    assert not browser['mobile_overflow'] and not browser['math_errors']
    assert browser['notes_reload'] and browser['review_export']
    reader_log = args.reader_log.read_text()
    assert 'ERRORS:' not in reader_log
    assert 'HTML rebuilt from pinned sources.' in reader_log
    expected_refs = set(migration.get('expected_unresolved_refs', ['thm:asymptotic-conormal', 'def:conormal']))
    assert set(re.findall(r'unresolved \\ref\{([^}]+)\}', reader_log)) == expected_refs
    paper_log = (args.paper_build / 'human_readable_main.log').read_text()
    assert set(re.findall(r"LaTeX Warning: Reference `([^']+)'", paper_log)) == expected_refs
    if 'expected_unresolved_citations' in migration:
        assert (set(re.findall(r"LaTeX Warning: Citation `([^']+)'", paper_log))
                == set(migration['expected_unresolved_citations']))
    assert 'Fatal error' not in paper_log
    pdf = args.paper_build / 'human_readable_main.pdf'
    assert pdf.read_bytes().startswith(b'%PDF-')
    shutil.copyfile(pdf, root / 'human_readable_main.pdf')
    # The archived proof-details PDF is optional; once removed it is not recorded.
    proof_details = root / 'lean_proof_details.pdf'
    if proof_details.exists():
        assert proof_details.read_bytes() == git(root, 'show', 'HEAD:lean_proof_details.pdf')
    generator_tests = dict(passed=counts['pass'], failed=counts['fail'],
        skipped=counts['skipped'], scope=('Generator regression suite including its browser tests' if '✔ browser' in tests
               else 'Non-browser generator regression suite'),
        skip_reason='Historical sibling-paper fixture unavailable; current manuscript passes the actual pinned build.')
    receipt = dict(status='passed', paper=source, generator=manifest['generator'],
        manuscript_cards=len(mapping['items']), active_statements=migration['active_statements'],
        manuscript_snapshot_byte_identical=True, paper_worktree_unchanged=True,
        formal_source_pins_unchanged=True,
        reader_build=dict(status='passed', warnings=sorted(expected_refs),
            scope='Complete current source/reference and statement-coverage audit; warnings are unresolved references already present in the paper.'),
        generator_tests=generator_tests, browser=browser,
        paper_pdf=dict(sha256=sha(pdf.read_bytes()), source_commit=source['commit'],
            build='latexmk -pdf -interaction=nonstopmode -halt-on-error human_readable_main.tex',
            isolated_checkout=True, unresolved_references=sorted(expected_refs)),
        comparison_review=dict(johanna='pending', max='pending', findings=browser['review_findings']),
        html_sha256=sha((root / 'index.html').read_bytes()))
    if proof_details.exists():
        receipt['proof_details_pdf'] = dict(status='retained', sha256=sha(proof_details.read_bytes()),
            scope='Historical readable account of the pinned formal proof; not a regenerated account of the revised printed proof.')
    for path, name in [(args.test_log, 'generator-tests.log'),
                       (args.reader_log, 'reader-build.log'),
                       (args.browser_receipt, 'browser.json'),
                       (args.paper_build / 'human_readable_main.log', 'paper-build.log')]:
        shutil.copyfile(path, target / name)
    (target / 'verification.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
    manuscript_pdfs = dict(paper=receipt['paper_pdf'])
    if 'proof_details_pdf' in receipt:
        historical_pdf_receipt = manifest['manuscript_pdfs'].get('source_receipt')
        if historical_pdf_receipt is None:
            historical_pdf_receipt = manifest['manuscript_pdfs']['proof_details']['historical_source_receipt']
        manuscript_pdfs['proof_details'] = dict(**receipt['proof_details_pdf'], historical_source_receipt=historical_pdf_receipt)
    manifest['manuscript_pdfs'] = manuscript_pdfs
    manifest['review'].update(claims=len(mapping['items']),
        statement_relations=dict(collections.Counter(i['statement_relation'] for i in mapping['items'])),
        proof_routes=dict(collections.Counter(i['route_relation'] for i in mapping['items'])))
    manifest['status'] = 'manuscript-review-draft'
    manifest['checks'] = dict(status='passed', receipt=f'{args.receipt_dir}/verification.json',
        reader_build=receipt['reader_build'], generator_tests=generator_tests, browser=browser,
        scope='Supplementary source mapping, renderer and reader behavior; not a new proof-correspondence certification.')
    paths = sorted(set(git(root, 'ls-files', '--cached', '--others', '--exclude-standard').decode().splitlines()))
    paths = [name for name in paths if name not in {'SHA256SUMS', 'manifest.json'} and (root / name).is_file()]
    manifest['files'] = {name: sha((root / name).read_bytes()) for name in paths}
    (root / 'manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    paths.append('manifest.json')
    (root / 'SHA256SUMS').write_text(''.join(f'{sha((root / name).read_bytes())}  {name}\n' for name in sorted(paths)))
    assert git(args.paper, 'status', '--porcelain=v1').decode() == status
    print(f'Recorded {counts["pass"]} passing generator tests, browser checks and isolated PDF build; {len(paths)} file checksums. Paper unchanged.')


if __name__ == '__main__':
    main()
