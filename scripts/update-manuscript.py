#!/usr/bin/env python3
"""Refresh the supplementary map from a committed paper without editing it.

The 2026-10-18 migration preserves the formal source pins and historical
verification receipts. Run rebuild.py afterwards to regenerate the reader.
"""
from pathlib import Path
import argparse
import collections
import copy
import hashlib
import json
import re
import subprocess


def git(repo, *args):
    return subprocess.check_output(['git', '-C', str(repo), *args], text=True)


def active_tex(raw):
    """Mask excluded text, retaining offsets and physical source lines."""
    raw = re.sub(r'(?<!\\)%[^\n]*', lambda m: ' ' * len(m[0]), raw)
    return re.sub(r'\\begin\{comment\}[\s\S]*?\\end\{comment\}',
                  lambda m: re.sub(r'[^\n]', ' ', m[0]), raw)


def environments(raw):
    result, stack = [], []
    for match in re.finditer(r'\\(begin|end)\{([^{}]+)\}', raw):
        kind, name = match.groups()
        if kind == 'begin':
            stack.append((name, match.start()))
        else:
            if not stack or stack[-1][0] != name:
                raise ValueError(f'Unbalanced environment {name}')
            _, start = stack.pop()
            result.append((name, start, match.end()))
    return sorted(result, key=lambda e: e[1])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper', type=Path, required=True)
    parser.add_argument('--commit', default='HEAD')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent.parent
    paper = args.paper.resolve()
    before = git(paper, 'status', '--porcelain=v1')
    commit = git(paper, 'rev-parse', args.commit).strip()
    raw = git(paper, 'show', f'{commit}:human_readable_main.tex')
    if (paper / 'human_readable_main.tex').read_text() != raw:
        raise SystemExit('Paper checkout differs from selected committed manuscript')
    clean = active_tex(raw)
    lines = clean.split('\n')
    envs = environments(clean)
    line_at = lambda pos: clean.count('\n', 0, pos) + 1
    labels = {m[1]: line_at(m.start())
              for m in re.finditer(r'\\label\{([^{}]+)\}', clean)}
    sections = [(line_at(m.start()), m[1]) for m in
                re.finditer(r'\\section\{([^\n]*)', clean)]
    section_bounds = [start for start, _ in sections] + [len(lines) + 1]
    statements = []
    kinds = set(re.findall(r'\\newtheorem\{([^{}]+)\}', clean))
    for name, start, end in envs:
        if name not in kinds:
            continue
        found = re.search(r'\\label\{([^{}]+)\}', clean[start:end])
        statements.append((name, found[1] if found else None,
                           line_at(start), line_at(end)))
    mapping = json.loads((root / 'paper-lean-map.json').read_text())
    manifest = json.loads((root / 'manifest.json').read_text())
    previous_receipt = root / 'verification/manuscript-20261018/migration.json'
    old_source = copy.deepcopy(mapping['sources']['paper'])
    if previous_receipt.exists():
        previous = json.loads(previous_receipt.read_text())
        if previous['current_paper']['commit'] == commit:
            old_source = previous['previous_paper']
    # These printed statements were removed, folded into another proof, or
    # placed inside a comment environment in the updated Overleaf source.
    removed = {'conv:H', 'lem:componentwise-involutive', 'reduction-k0',
               'lem:tangent-limit', 'def:noncar', 'prop:noncar'}
    items = [i for i in mapping['items'] if i['id'] not in removed]

    def line_of(text):
        pos = clean.find(text)
        if pos < 0:
            raise ValueError(f'Missing manuscript anchor {text!r}')
        return line_at(pos)

    def section_end(start):
        return next(x - 1 for x in section_bounds if x > start)

    def labelled_range(label):
        line = labels[label]
        matches = [e for e in envs if line_at(e[1]) <= line <= line_at(e[2])
                   and e[0] in kinds]
        if not matches:
            raise ValueError(f'No statement environment for {label}')
        _, start, end = matches[-1]
        a, b = line_at(start), line_at(end)
        limit = min([s[2] - 1 for s in statements if s[2] > b]
                    + [section_end(a)])
        # Include following proofs and formal references, but not the next
        # statement. The base-change lemma needs its own card before the
        # unnumbered final proof.
        if label == 'lem:base-change':
            limit = line_of(r'\noindent\textbf{Proof of Theorem') - 1
        elif label == 'thm:asymptotic-conormal-formal':
            proof_start = next(e for e in envs if e[0] == 'proof' and e[1] > end)
            limit = line_at(proof_start[1]) - 1
        return [a, limit]

    renamed = {'thm:asymptotic-conormal': 'thm:asymptotic-conormal-formal',
               'lem:initial-base-change': 'lem:base-change'}
    for item in items:
        label = renamed.get(item['id'], item.get('label'))
        if label and label in labels and any(s[1] == label for s in statements):
            item['label'] = label
            item['tex_lines'] = labelled_range(label)
        item.pop('pdf_page', None)  # A new PDF must supply its own page anchors.

    euler = line_of(r'\section{$x_1$ as a surjective map}')
    cokernel = line_of(r'\section{Vanishing cokernel}')
    conormal = line_of(r'\section{A conormal direction at infinity}')
    theorem_proof = next(e for e in envs if e[0] == 'proof' and
                         line_at(e[1]) > labels['thm:asymptotic-conormal-formal'])
    ranges = {
        'abstract': [line_of(r'\begin{abstract}'), line_of(r'\end{abstract}')],
        'thm:main': [line_of(r'Let $k$ be a field'), line_of(r'\AIadd{The machine-checked proof') - 1],
        'challenge-main': [labels['thm:main'], line_of(r'\AIadd{The machine-checked proof') - 1],
        'challenge-fixed-source': [labels['thm:main'], line_of(r'\AIadd{The machine-checked proof') - 1],
        'global-stafford': [line_of(r'\AIadd{The machine-checked proof'), line_of(r'\textit{Proof sketch:}') - 1],
        'intro-proof-sketch': [line_of(r'\textit{Proof sketch:}'), line_of(r'\AIadd{Constructive predecessors') - 1],
        'context-prior-art': [line_of(r'\AIadd{Constructive predecessors'), line_of(r'\section{\texorpdfstring') - 1],
        'formal-verification': [line_of(r'\section{\texorpdfstring'), line_of(r'\section{Notation and definitions}') - 1],
        'cotangent': [labels['sec:cotangent'], labelled_range('def:good-filtration')[0] - 1],
        'monic-scalar': [line_of(r'If $N=0$'), line_of(r'We want to construct a well-behaved') - 1],
        'phi-g': [line_of(r'Let $g$ be a $k$-linear automorphism'), labelled_range('prop:monic')[0] - 1],
        'eq:I-Q': [euler + 1, line_of(r'The commutator of $E$') - 1],
        'euler-grading': [line_of(r'The commutator of $E$'), labelled_range('lem:euler')[0] - 1],
        'vc-setup': [line_of(r'For this section, we write $M='), labelled_range('def:length')[0] - 1],
        'dir-def': [conormal + 1, labelled_range('def:dir')[1]],
        'thm:asymptotic-conormal-proof': [line_at(theorem_proof[1]), section_end(line_at(theorem_proof[1]))],
        'proof-main': [line_of(r'\noindent\textbf{Proof of Theorem'), labelled_range('cor:cyclic')[0] - 1],
        'outlook': [line_of(r'\section{Outlook}'), line_of(r'\clearpage') - 1],
        'ai-workflow': [labels['app:ai-workflow'], line_of(r'\section{Further work}') - 1],
        'further-work': [line_of(r'\section{Further work}'), line_of(r'\end{appendix}') - 1],
        'appendix-right-ore': [line_of(r'the identity in every right Ore localization'), line_of(r'the left-handed identity') - 1],
        'appendix-left-handed': [line_of(r'the left-handed identity'), line_of(r'the identity for finite-order differential') - 1],
        'appendix-localized-differential': [line_of(r'the identity for finite-order differential'), line_of(r'and, independently of the geometric') - 1],
        'appendix-evolutionary': [line_of(r'and, independently of the geometric'), line_of(r'\AIcomment{SCOPE-01}') - 1],
    }
    for item in items:
        if item['id'] in ranges:
            item['tex_lines'] = ranges[item['id']]
        if item['section'] in {'3', '3.1', '3.2'}:
            start = item['tex_lines'][0]
            item['section'] = ('3.2' if start >= line_of(r'\subsection{Gabber')
                               else '3.1' if start >= labels['sec:cotangent'] else '3')
        item['depends_on'] = [x for x in item.get('depends_on', []) if x not in removed]
        if item.get('label') not in labels:
            item.pop('label', None)

    by_id = {i['id']: i for i in items}
    def add(label, section, title, refs=(), relation='partial', route='n/a', note=''):
        if label in by_id:
            return
        kind = next(s[0].title() for s in statements if s[1] == label)
        item = dict(id=label, label=label, section=section, kind=kind, number='',
                    short=title, title=title, tex_lines=labelled_range(label),
                    statement_relation=relation, route_relation=route,
                    correspondence=note, route=None, lean=list(refs),
                    depends_on=[], in_graph=False, graph_sub=None, graph_order=0,
                    auditors=[], review_scope='publication', historical_issues=[], issues=[])
        items.append(item)
        by_id[label] = item

    ref = lambda file, name, repo='formal': dict(file=file, name=name, repo=repo, role='supporting result')
    add('def:localization', '6', 'Localization at a multiplicative set', note=
        'Standard localization definition used by the localized length arguments. No new formal theorem is claimed for this definition.')
    add('def:supp', '6', 'Support of a module', note=
        'Support is defined by nonzero localization. The subsequent Lean comparisons use this meaning; this vocabulary card does not claim a separate proof.')
    add('lem:supp-criterion', '6', 'Support via the annihilator of an element', note=
        'The manuscript now proves the element-annihilator criterion explicitly. The mapped finiteness and localization results consume support; a declaration proving this exact printed lemma is not asserted here.', route='similar')
    add('lem:place', '8', 'A divisorial place with a vanishing first coordinate', refs=[
        ref('Stafford38/Geometry/GeneralDivisorialVisibleFrame.lean', 'Stafford38.Geometry.GeneralDivisorialVisibleFrame.generalDivisorialVisibleFrameWithResidueAlgebraicity')],
        route='similar', note='The printed proof constructs a valuation ring, normalizes a finite-type chart and localizes at a height-one prime. The cited formal result supplies a divisorial visible frame with residue algebraicity. Compare all chart and valuation hypotheses; an exact wrapper for every clause is not claimed.')
    add('lem:kappa', '8', 'Residue field and differential basis', refs=[
        ref('Stafford38/Geometry/KaehlerDVRVisibility.lean', 'Stafford38.Geometry.KaehlerDVRVisibility.kaehler_span_of_isAlgebraic_adjoin')],
        route='similar', note='The new residue-field lemma separates algebraicity, a differential basis and finite generation of differentials. The cited formal result supports the differential span argument; it does not by itself certify all three printed clauses.')
    add('lem:tangent', '8', 'Tangent space at the Laurent generic point', refs=[
        ref('Stafford38/Geometry/PaperSameWitnessTangentDimension.lean', 'Stafford38.Geometry.PaperSameWitnessTangentDimension.tangent_finrank_le_residue_add_one_of_witness')],
        route='similar', note='The dimension bound has a named formal analogue for the retained witness. The printed quotient-rule argument and affine conormal conclusion require comparison of their own hypotheses; this card does not mark the complete three-part lemma exact.')
    add('thm:nss', '9', "Hilbert's Nullstellensatz", note=
        'Standard algebraically closed-field Nullstellensatz, now stated explicitly. Lean uses ideal/zero-locus results in the mapped geometric proofs; no separate new verification receipt is claimed.')
    # Number theorem-like environments as the manuscript does: one shared
    # counter per section, including definitions and conventions.
    counts = collections.Counter()
    numbered = {}
    for kind, label, a, b in statements:
        sec = str(sum(start <= a for start, _ in sections))
        counts[sec] += 1
        if label:
            numbered[label] = f'{sec}.{counts[sec]}'
    for item in items:
        if item.get('label') in numbered:
            item['number'] = numbered[item['label']]
            item['short'] = f"{item['kind']} {item['number']}"
        # Old substep ranges describe the previous revision. A current card's
        # exact source range is authoritative until substeps are reviewed.
        for step in item.get('steps', []):
            step.pop('tex_lines', None)
    by_id['dir-def']['label'] = 'def:dir'
    by_id['dir-def']['number'] = numbered['def:dir']
    by_id['lem:initial-base-change'].update(title='Base change of the canonical quotient and its characteristic variety',
        correspondence='The updated lemma states associated-graded base change, annihilator equality for the finite graded module, and faithful field descent for the canonical quotient. The retained Lean references prove the two order-initial-ideal inclusions and equality. The full module isomorphism and support-preimage formulation require separate comparison.', statement_relation='partial')
    by_id['prop:monic']['correspondence'] = 'The revised proof makes the transpose convention, symbol substitution and PBW coefficient calculation explicit. The retained formal references cover symplectic normalization and the right-monic decomposition; compare row/column conventions and the Bernstein degree bounds.'
    by_id['prop:x-surjective']['correspondence'] = 'Both arguments derive coordinate surjectivity from the Euler residue and one-sided normality. The paper now proves stability of q A_{>=0} under C and p; Lean uses an elementwise closure argument. The proof routes are similar, with the same surjectivity conclusion.'
    by_id['prop:x-surjective']['route_relation'] = 'similar'
    by_id['lem:tangential-finiteness']['correspondence'] = 'The expanded proof derives tangential finiteness from the monic quotient and proves kernel-support containment by localized surjectivity and Vasconcelos. Finite length at a minimal support prime remains stated without a separate final proof paragraph. The retained formal references and the length card expose the corresponding finite-length input.'
    by_id['lem:page-inequality']['correspondence'] = 'The expanded proof gives explicit filtered pages, their T-action, localization, exhaustion, stabilization and telescoping of lengths. The formal page inequality and uniform boundary-vanishing result are the comparison targets. The asserted commutative T-action and T-linearity on higher pages still require Max’s proof correspondence review.'
    by_id['lem:strict-support-inequality']['correspondence'] = 'The updated proof derives minimal-prime involutivity by localization, excludes x1 by iterated brackets, and proves strict length positivity using stabilized power kernels and Nakayama. The printed localization notation changes between the tangential prime and a symbol-ring prime; this requires clarification in review. The paper is preserved verbatim.'
    by_id['prop:char-avoids']['correspondence'] = 'The manuscript gives two consecutive proofs of support avoidance. Both use Supp(M/x1M) = Supp(M) intersect V(x1) and U=0. Both are retained verbatim. The formal support statement is transported along the fibre sign change, which fixes x1.'
    new_issues = {
        'formal-verification': ('MS18-REF-01', 'The manuscript references thm:asymptotic-conormal, but the active theorem is labelled thm:asymptotic-conormal-formal.', 'Review the stale cross-reference in the paper.'),
        'thm:coisotropic-exclusion': ('MS18-REF-02', 'The manuscript references def:conormal, which is now inside a comment environment. Some displayed containments also mix fibre covectors and cotangent pairs.', 'Review the missing definition reference and the ambient spaces of the conormal containments.'),
        'prop:char-avoids': ('MS18-DUP-01', 'The proposition is followed by two consecutive proofs of the same support identity.', 'Review whether both proofs should remain in the paper.'),
        'lem:kappa': ('MS18-ORDER-01', 'The proof uses q0=q1=0 and j not in {0,1}; the argument establishing these facts occurs later in the theorem proof.', 'Check the dependency order or supply the valuation argument before this lemma.'),
        'lem:strict-support-inequality': ('MS18-NOTATION-01', 'The proof introduces I as a radical annihilator but then names J, and alternates between the tangential prime q and a symbol-ring prime p in localization subscripts.', 'Clarify the commutative symbol ring, radical ideal and localization maps in review.'),
    }
    for identifier, (issue_id, summary, fix) in new_issues.items():
        issue = dict(id=issue_id, severity='minor', summary=summary, fix=fix,
                     aicomment=None, status='open; paper preserved verbatim')
        by_id[identifier]['issues'] = [issue]
    by_id['thm:asymptotic-conormal'].update(title='Asymptotic conormal direction over an algebraically closed field',
        correspondence='The active statement now includes both polynomial vanishing at the coordinate axis and projective conormal-direction membership over any algebraically closed characteristic-zero field. The retained Lean results prove the corresponding affine-cone and projective conclusions. Proof correspondence remains separate.', depends_on=['lem:place', 'lem:kappa', 'lem:tangent'])
    by_id['thm:asymptotic-conormal-proof']['correspondence'] = 'The active printed proof now uses a divisorial valuation, residue-field derivations, a Laurent generic tangent frame, a unit minor, and specialization of polynomial conormal identities. The former complex closed-point/tilted-arc proof is inside a comment environment and is not current manuscript text. The unchanged formal endpoint still assembles the retained SameWitness route; the generic/Laurent declarations are comparison material, not evidence that the selected formal endpoint follows this revised printed proof step by step.'
    by_id['thm:asymptotic-conormal-proof']['route_relation'] = 'similar'
    by_id['thm:coisotropic-exclusion']['correspondence'] = 'The expanded proof establishes fibre homogeneity, the zero section over the projected base, Hamiltonian translations, component conormal containment and the axis contradiction. It allows any fibre polynomial nonzero at the coordinate axis, without a homogeneity hypothesis on P, matching the mapped formal scope. Some conormal containments in the printed proof mix fibre and cotangent-space notation; the supplementary preserves the text and records this review issue.'
    refreshed = {'prop:monic', 'prop:x-surjective', 'lem:tangential-finiteness',
                 'lem:page-inequality', 'lem:strict-support-inequality',
                 'prop:char-avoids', 'thm:asymptotic-conormal',
                 'thm:asymptotic-conormal-proof', 'thm:coisotropic-exclusion',
                 'lem:initial-base-change', 'def:localization', 'def:supp',
                 'lem:supp-criterion', 'lem:place', 'lem:kappa', 'lem:tangent', 'thm:nss'}
    for identifier in refreshed:
        by_id[identifier]['comparison_updated_on'] = '2026-10-18'
    for identifier in ['thm:asymptotic-conormal-proof', 'thm:coisotropic-exclusion']:
        by_id[identifier].pop('steps', None)
    by_id['proof-main']['depends_on'] = ['prop:monic', 'prop:x-surjective', 'prop:char-avoids', 'thm:coisotropic-exclusion', 'lem:initial-base-change']
    tie_order = {'challenge-main': 1, 'challenge-fixed-source': 2}
    items.sort(key=lambda i: (i['tex_lines'][0], tie_order.get(i['id'], 0)))
    source = dict(repo='itpplasma/stafford38-paper', commit=commit,
                  file='human_readable_main.tex', origin_repo='itpplasma/stafford38-paper',
                  origin_commit=commit, sha256=hashlib.sha256(raw.encode()).hexdigest(),
                  label='Paper (Overleaf update)', local_source_base='./sources/paper',
                  note='October 18 Overleaf update, preserved verbatim. Excluded comment environments are not current manuscript passages.')
    snapshot_files = {}
    snapshot_base = root / 'sources/paper/raw'
    snapshot_base.mkdir(parents=True, exist_ok=True)
    for file in ['human_readable_main.tex', 'references.bib', 'ai_review.tex']:
        content = git(paper, 'show', f'{commit}:{file}')
        (snapshot_base / file).write_text(content)
        snapshot_files[file] = hashlib.sha256(content.encode()).hexdigest()
    source['snapshot'] = dict(base='sources/paper/raw', files=snapshot_files)
    mapping['version'] = '0.2.4-manuscript-review'
    mapping['subtitle'] = 'October 18 manuscript · paper and Lean proof comparison'
    mapping['reader_notice'] = 'Manuscript updated 18 October 2026. Five review findings are recorded under Comparison notes. Formal proof details retain their archived source scope.'
    mapping['sources']['paper'] = source
    mapping['items'] = items
    mapping['aicomments'] = [dict(id=m[1], line=line_at(m.start()), verdict='author review pending',
        note='Active annotation in the updated manuscript; no author acceptance is inferred.')
        for m in re.finditer(r'\\AIcomment\{([^{}]+)\}', clean)]
    mapping['sections'][-1]['title'] = 'Appendix B: Further work'
    mapping['provenance'] = '<p>The paper passages are the October 18 Overleaf update, pinned and reproduced verbatim. The formal source pins and historical verification receipts are retained. Mathematical edits to the manuscript have not been made by this supplementary update. Comparison labels do not certify a revised printed proof.</p>'
    mapping['comparison_scope'] = 'The active October 18 manuscript, including visible AI markup. Comment environments are excluded. Unchanged Lean source pins retain their previous verification scope; updated printed proofs require fresh human correspondence review.'
    mapping['overview'] = 'Compare the October 18 Overleaf manuscript with the pinned Lean results. Newly expanded support, divisorial and Laurent-tangent arguments are represented explicitly. Commented-out proofs are excluded. The selected formal endpoint still follows its recorded SameWitness route; matching conclusions do not certify the revised printed proof step by step. Johanna’s author review and Max’s correspondence review remain pending.'
    mapping['candidate']['status'] = 'October 18 manuscript refresh; formal source pins unchanged; human correspondence review pending'
    mapping['candidate']['manuscript'] = source
    mapping['same_witness_declaration_map_candidate']['status'] = 'Historical comparison against the October 3 manuscript; not a line map for the revised October 18 generic/Laurent proof.'
    manifest['version'] = mapping['version']
    manifest['sources']['paper'] = source
    manifest['review'].update(claims=len(items), scope=mapping['comparison_scope'],
        statement_relations=dict(collections.Counter(i['statement_relation'] for i in items)),
        proof_routes=dict(collections.Counter(i['route_relation'] for i in items)))
    manifest['status'] = 'manuscript-update-in-progress'
    manifest['checks'] = dict(status='pending', receipt='verification/manuscript-20261018/verification.json',
        note='Historical canonical-definition checks remain in their original receipt; they do not verify the updated manuscript build.')
    # The actual PDFs are refreshed by the isolated manuscript build, never
    # by compiling in the authoritative paper checkout.
    manifest['manuscript_pdfs']['current_paper_commit'] = commit
    manifest['manuscript_pdfs']['paper_pdf_status'] = 'rebuild-required'
    history = dict(previous_paper=old_source, current_paper=source,
                   removed_cards=sorted(removed), active_statements=len(statements),
                   current_cards=len(items), paper_worktree_status_before=before,
                   note='The paper repository is read-only throughout this migration.')
    for label in labels:
        if any(s[1] == label for s in statements) and not any(i.get('label') == label for i in items):
            raise ValueError(f'Unmapped active statement {label}')
    for i in items:
        a, b = i['tex_lines']
        if not 1 <= a <= b <= len(lines):
            raise ValueError(f'Invalid range for {i["id"]}: {a}-{b}')
    if git(paper, 'status', '--porcelain=v1') != before:
        raise SystemExit('Paper worktree changed during migration')
    receipt_dir = root / 'verification/manuscript-20261018'
    receipt_dir.mkdir(parents=True, exist_ok=True)
    (receipt_dir / 'migration.json').write_text(json.dumps(history, indent=2, ensure_ascii=False) + '\n')
    for name, value in [('paper-lean-map.json', mapping), ('manifest.json', manifest)]:
        (root / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    print(f'Pinned manuscript {commit[:12]}; {len(items)} cards; {len(statements)} active statements. Paper unchanged.')


if __name__ == '__main__':
    main()
