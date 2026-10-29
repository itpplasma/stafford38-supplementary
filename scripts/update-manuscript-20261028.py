#!/usr/bin/env python3
"""Map the reader to the October 28 manuscript layout without editing the paper.

The October 28 Overleaf update rewrites the preliminaries: Subsection 2.1 is
replaced by numbered definitions (torsion and cyclic modules, cotangent
bundle, spectrum and vanishing loci, symplectic form, Poisson bracket), the
Nullstellensatz gains a closed-point clause, and Section 5.1 adds definitions
of valuation rings and of the conormal space. Every printed AI proposal is
resolved in the text, the proof of Proposition 3.6 follows its statement and
Section 7 no longer lists the right Ore localization. update-manuscript.py
and update-manuscript-20261021.py record the earlier migrations and are kept
unchanged for reproducibility.

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

ROOT = Path(__file__).resolve().parent.parent
RECEIPT = ROOT / 'verification/manuscript-20261028'
_spec = importlib.util.spec_from_file_location('update_manuscript', ROOT / 'scripts/update-manuscript.py')
um = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(um)
git, active_tex, environments = um.git, um.active_tex, um.environments

# Card ids are kept stable (they key saved review notes); labels follow the paper.
RENAMED = {'cotangent': 'def:cotangent', 'def:symplectic-poisson': 'def:symplectic'}
# Labels of the October 21 source that no longer exist.
DELETED_LABELS = ['def:symplectic-poisson', 'sec:cotangent']
# Cards whose passage is gone: the proof of Proposition 3.6 now follows the
# statement and belongs to its card; Section 7 drops the right Ore localization.
REMOVED = ['prop:charP-proof', 'appendix-right-ore']
# Printed names of theorem environments that differ from the environment name.
PRINTED = {'convention': 'Notation'}
SECTIONS = [
    ('1', 'Introduction', None), ('1.1', 'Related literature', None),
    ('1.2', 'Formal verification with Lean', 'sec:formal'),
    ('2', 'Preliminaries', 'sec:setting'),
    ('3', 'Mapping to a normal form', 'sec:monic'),
    ('4', 'x\u2081 as a surjective map', 'sec:euler'),
    ('5', 'Avoiding the hyperplane {x\u2081 = 0}', 'sec:conormal-review'),
    ('5.1', 'Preliminaries and definitions from algebraic geometry', 'sub:def_geom'),
    ('5.2', 'Proof of Theorem 5.7', 'sub:asym'),
    ('5.3', 'Proof of Theorem 5.8', 'sub:excl'),
    ('6', 'Proof of Theorem 1.1', 'sec:proof'),
    ('7', 'Generalizations and open questions', 'sec:generalizations'),
    ('A', 'Appendix A: AI-assisted research and formalization', 'app:ai-workflow'),
]
STATEMENT_WORDS = (r'(?:Definitions?|Lemmas?|Theorems?|Propositions?|Corollar(?:y|ies)|'
                   r'Conventions?|Notation|Remarks?)')
NUMBER_LIST = re.compile(STATEMENT_WORDS + r'\s+(?:\d+\.\d+(?:\([a-z]\))?(?:\s*(?:,|–|and)\s*)?)+')


def statement_numbers(clean, line_at):
    kinds = set(re.findall(r'\\newtheorem\{([^{}]+)\}', clean))
    section_lines = [line_at(m.start()) for m in re.finditer(r'\\section\{', clean)]
    counts, numbered, statements = collections.Counter(), {}, []
    for name, start, end in environments(clean):
        if name in kinds:
            found = re.search(r'\\label\{([^{}]+)\}', clean[start:end])
            statements.append((name, found[1] if found else None, line_at(start), line_at(end)))
    for kind, label, a, _ in statements:
        sec = str(sum(start <= a for start in section_lines))
        counts[sec] += 1
        numbered[label] = f'{sec}.{counts[sec]}'
    return statements, numbered


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper', type=Path, required=True)
    parser.add_argument('--commit', required=True)
    parser.add_argument('--base-rev', default='HEAD',
                        help='Supplementary revision whose map and manifest are migrated.')
    args = parser.parse_args()
    paper = args.paper.resolve()
    before = git(paper, 'status', '--porcelain=v1')
    commit = git(paper, 'rev-parse', args.commit).strip()
    base_rev = git(ROOT, 'rev-parse', args.base_rev).strip()
    raw = git(paper, 'show', f'{commit}:human_readable_main.tex')
    clean = active_tex(raw)
    lines = clean.split('\n')
    envs = environments(clean)
    line_at = lambda pos: clean.count('\n', 0, pos) + 1
    labels = {m[1]: line_at(m.start()) for m in re.finditer(r'\\label\{([^{}]+)\}', clean)}
    statements, numbered = statement_numbers(clean, line_at)
    unlabelled = [s for s in statements if not s[1]]
    if unlabelled:
        raise ValueError(f'Unlabelled statements need a card id: {unlabelled}')
    heads = [(line_at(m.start()), m[1]) for m in
             re.finditer(r'\\(section|subsection)\{', clean)]
    bounds = [a for a, _ in heads] + [len(lines) + 1]
    proofs = [(line_at(a), line_at(b)) for n, a, b in envs if n == 'proof']

    mapping = json.loads(git(ROOT, 'show', f'{base_rev}:paper-lean-map.json'))
    manifest = json.loads(git(ROOT, 'show', f'{base_rev}:manifest.json'))
    old_source = mapping['sources']['paper']
    if old_source['commit'] == commit:
        raise SystemExit('Base revision is already migrated; pass --base-rev of the October 21 map')
    old_clean = active_tex(git(paper, 'show', f"{old_source['commit']}:human_readable_main.tex"))
    old_line_at = lambda pos: old_clean.count('\n', 0, pos) + 1
    _, old_numbered = statement_numbers(old_clean, old_line_at)
    # Old printed number -> new printed number, for statements that kept their label.
    renumber = {old_numbered[l]: numbered[l] for l in old_numbered if l in numbered}
    renumber[old_numbered['def:symplectic-poisson']] = numbered['def:symplectic']
    items = mapping['items']
    by_id = {i['id']: i for i in items}

    def line_of(text, after=0):
        start = 0
        for _ in range(after):
            start = clean.index('\n', start) + 1
        pos = clean.find(text, start)
        if pos < 0:
            raise ValueError(f'Missing manuscript anchor {text!r}')
        return line_at(pos)

    def next_bound(line):
        return next(x - 1 for x in bounds if x > line)

    def enclosing_proof(line):
        return [p for p in proofs if p[0] < line <= p[1]]

    def labelled_range(label):
        _, _, a, b = next(s for s in statements if s[1] == label)
        if enclosing_proof(a):
            # Lemmas stated inside a longer proof: the statement and its own
            # proof; the surrounding text belongs to the enclosing proof card.
            own = [p for p in proofs if b < p[0] <= b + 2]
            return [a, own[0][1] if own else b]
        limit = min([s[2] - 1 for s in statements if s[2] > b] + [next_bound(a)])
        if label == 'lem:base-change':
            limit = line_of(r'Let $d\in A_n(k)$ be nonzero of Bernstein degree') - 1
        return [a, limit]

    def renumbered(text):
        if not text:
            return text
        return NUMBER_LIST.sub(lambda m: re.sub(r'\d+\.\d+', lambda n: renumber.get(n[0], n[0]), m[0]), text)

    # ---------------------------------------------------- removed cards ----
    charP = by_id['cor:charP']
    for ref in by_id['prop:charP-proof']['lean']:
        if ref['name'] not in {r['name'] for r in charP['lean']}:
            charP['lean'].append(ref)
    removed = {i: by_id.pop(i) for i in REMOVED}
    items[:] = [i for i in items if i['id'] not in removed]
    for item in items:
        item['depends_on'] = [d for d in item['depends_on'] if d not in removed]

    # ---------------------------------------------------- existing cards ----
    for item in items:
        label = RENAMED.get(item['id'], item.get('label'))
        if label and any(s[1] == label for s in statements):
            item['label'] = label
            item['tex_lines'] = labelled_range(label)
        elif item.get('label') and item['label'] not in labels:
            item.pop('label', None)
    gen = labels['sec:generalizations']
    ranges = {
        'abstract': [line_of(r'\begin{abstract}'), line_of(r'\end{abstract}')],
        'thm:main': [line_of(r'Let $k$ be a field'), line_of(r'\textit{Proof sketch:}') - 1],
        'challenge-main': [labels['thm:main'], line_of(r'\textit{Proof sketch:}') - 1],
        'challenge-fixed-source': [labels['thm:main'], line_of(r'\textit{Proof sketch:}') - 1],
        'intro-proof-sketch': [line_of(r'\textit{Proof sketch:}'), line_of(r'\subsection{Related literature}') - 1],
        'context-prior-art': [line_of(r'\subsection{Related literature}'), labels['sec:formal'] - 1],
        'formal-verification': [labels['sec:formal'], labels['sec:setting'] - 1],
        'monic-scalar': [line_of(r'If $N=0$'), line_of(r'We want to construct a well-behaved') - 1],
        'phi-g': [line_of(r'Let $g$ be a $k$-linear automorphism'), labelled_range('prop:monic')[0] - 1],
        'eq:I-Q': [line_of(r'We will now define the modules'), line_of(r'We now use the order filtration') - 1],
        'euler-grading': [labels['sec:euler'] + 1, labelled_range('lem:euler')[0] - 1],
        'vc-setup': [line_of(r'For this part, we write $M='), labelled_range('lem:tangential-finiteness')[0] - 1],
        'thm:asymptotic-conormal-proof': [labels['sub:asym'], labels['sub:excl'] - 1],
        'thm:coisotropic-exclusion-proof': [labels['sub:excl'], labels['sec:proof'] - 1],
        'conormal-intro': [labels['sec:conormal-review'], labels['sub:def_geom'] - 1],
        'proof-main': [line_of(r'Let $d\in A_n(k)$ be nonzero of Bernstein degree'), labelled_range('cor:cyclic')[0] - 1],
        'further-work': [gen, line_of('Two further results', gen) - 1],
        'appendix-left-handed': [line_of('the left-handed identity', gen), line_of('the identity for finite-order', gen)],
        'appendix-localized-differential': [line_of('the identity for finite-order', gen), line_of('of the geometric part of Section', gen) - 1],
        'appendix-evolutionary': [line_of('of the geometric part of Section', gen) - 1, line_of('provided each $a_j$ commutes', gen)],
        'global-stafford': [line_of(r'\item Let $A$ be a smooth'), line_of(r'\item Let $U$ be an infinite') - 1],
        'generalization-filtered': [line_of(r'\item Let $U$ be an infinite'), line_of(r'\end{enumerate}', gen)],
        'outlook': [line_of(r'The proof of Theorem~\ref{thm:main} shows $Q=0$'), line_of(r'\bibliographystyle') - 1],
        'ai-workflow': [labels['app:ai-workflow'], line_of(r'\end{appendix}') - 1],
    }
    for identifier, value in ranges.items():
        by_id[identifier]['tex_lines'] = value

    # ------------------------------------------------- resolved findings ----
    resolved = {
        'thm:coisotropic-exclusion-proof': 'MS18-REF-02', 'lem:strict-support-inequality': 'MS18-NOTATION-01',
        'conormal-intro': 'MS21-CITE-01', 'intro-proof-sketch': 'MS21-TODO-01', 'cor:charP': 'MS21-PROOF-01',
        'thm:asymptotic-conormal-proof': 'MS21-REF-03', 'lem:kappa': 'MS21-KAPPA-01'}
    for identifier, issue_id in resolved.items():
        issue = next(i for i in by_id[identifier]['issues'] if i['id'] == issue_id)
        issue['status'] = f'resolved in paper {commit[:7]}'
        by_id[identifier]['issues'].remove(issue)
        by_id[identifier].setdefault('historical_issues', []).append(issue)
    # Proposed changes whose AI markup is gone: the manuscript now prints no
    # \AIadd proposal outside Lean references and no \AIremove.
    assert not re.search(r'\\AIadd\{(?!\\formalref)', clean) and r'\AIremove' not in clean
    for item in items:
        for issue in [i for i in item['issues'] if i.get('status') == 'author acceptance pending']:
            issue['status'] = f'AI proposal markup no longer in the manuscript at {commit[:7]}'
            item['issues'].remove(issue)
            item.setdefault('historical_issues', []).append(issue)
    # Existing texts cite October 21 numbers; history keeps its numbering.
    for item in items:
        item['correspondence'] = renumbered(item['correspondence'])
        item['title'] = renumbered(item['title'])
        for issue in item['issues']:
            issue['summary'], issue['fix'] = renumbered(issue['summary']), renumbered(issue['fix'])

    # ------------------------------------------------------- new cards ----
    def add(identifier, title, label, refs=(), relation='partial', route='n/a', note=''):
        kind = next(s[0].title() for s in statements if s[1] == label)
        item = dict(id=identifier, section='', kind=kind, number='', short=title,
                    title=title, tex_lines=labelled_range(label), statement_relation=relation,
                    route_relation=route, correspondence=note, route=None, lean=list(refs),
                    depends_on=[], in_graph=False, graph_sub=None, graph_order=0,
                    auditors=[], review_scope='publication', historical_issues=[], issues=[],
                    label=label)
        items.append(item)
        by_id[identifier] = item

    def ref(file, name, role='definition'):
        return dict(file=file, name=name, repo='formal', role=role)

    add('def:cyclic', 'Torsion and cyclic modules', 'def:cyclic', refs=[
        ref('Stafford38/ChallengeDefinitions.lean', 'Stafford38.TorsionCyclicity.IsRightTorsion')],
        note='New definition of torsion and cyclic right A_n(k)-modules, the vocabulary of Corollary 6.3. Lean IsRightTorsion is the torsion hypothesis of the formal corollary; cyclicity is stated there through the span of one element. Neither is compared clause by clause here.')
    add('def:spec', 'Spectrum, vanishing loci and vanishing ideals', 'def:spec',
        note='New definition: Spec S, the vanishing locus V(J), the classical zero set V_K(J), the vanishing ideal I(S), and a ∈ V_K(J) iff 𝔪_a ∈ V(J). The formal sources work with Mathlib prime spectra and zero loci; no separate formal declaration is mapped for this definition.')
    add('def:poisson', 'Poisson bracket on k[x,ξ]', 'def:poisson', relation='exact', refs=[
        ref('Stafford38/Characteristic/Polynomial.lean', 'Stafford38.Characteristic.poissonBracket')],
        note='Now a separate definition. Lean poissonBracket f g = Σᵢ (∂f/∂xᵢ · ∂g/∂ξᵢ − ∂f/∂ξᵢ · ∂g/∂xᵢ), the printed bracket with the same sign; PhaseVar .inl indexes xᵢ and .inr indexes ξᵢ. Earlier cards recorded the opposite sign, which does not match the printed formula.')
    add('def:valuation', 'Valuation rings, discrete valuation rings and Laurent series', 'def:valuation',
        note='New definition of the vocabulary of Lemmas 5.9 and 5.10: valuation rings, discrete valuation rings with ord_V, and κ[[t]], κ((t)). The formal sources use the Mathlib notions (valuation rings, discrete valuation rings, power and Laurent series); no separate formal declaration is mapped for this definition.')
    add('def:conormal', 'Irreducibility, smooth locus, conormal space and conormal cone', 'def:conormal', refs=[
        ref('Stafford38/Geometry/SmoothAffineConormal.lean', 'Stafford38.Geometry.SmoothAffineConormal.SmoothAffinePoint'),
        ref('Stafford38/Geometry/AffineConormalSpan.lean', 'Stafford38.Geometry.AffineConormalSpan.affineConormalSpace')],
        note='The label def:conormal, cited but missing on October 21, exists again. Irreducibility is primality of I(Y); the smooth locus is defined by the Jacobian rank, and its density is cited, not proved. Lean uses the same declarations as the Dir(Y) card: SmoothAffinePoint for smooth points and affineConormalSpace for the span of the differentials dfᵧ.')

    # ------------------------------------------- sections and numbering ----
    sec_line = {number: (labels[label] if label else None) for number, _, label in SECTIONS}
    sec_line['1'] = line_of(r'\section{Introduction}')
    sec_line['1.1'] = line_of(r'\subsection{Related literature}')
    ordered = sorted((line, number) for number, line in sec_line.items())
    mapping['sections'] = [dict(number=n, title=t, **({'label': l} if l else {})) for n, t, l in SECTIONS]
    for item in items:
        start = item['tex_lines'][0]
        item['section'] = ([n for line, n in ordered if line <= start] or ['1'])[-1]
    kind_of = {s[1]: PRINTED.get(s[0], s[0].title()) for s in statements}
    for item in items:
        if item.get('label') in numbered:
            item['number'] = numbered[item['label']]
            item['kind'] = kind_of[item['label']]
            item['short'] = f"{item['kind']} {item['number']}"
        for step in item.get('steps', []):
            step.pop('tex_lines', None)
    assert numbered['thm:asymptotic-conormal-formal'] == '5.7' and numbered['thm:coisotropic-exclusion'] == '5.8'
    shorts = {'thm:asymptotic-conormal-proof': 'Proof of 5.7', 'thm:coisotropic-exclusion-proof': 'Proof of 5.8'}
    for identifier, short in shorts.items():
        by_id[identifier]['short'] = short
    for identifier, kind, number in [
            ('thm:asymptotic-conormal-proof', 'Proof', 'of 5.7'),
            ('thm:coisotropic-exclusion-proof', 'Proof', 'of 5.8')]:
        by_id[identifier].update(kind=kind, number=number)

    # ---------------------------------------------------------- findings ----
    definition =next(i for i in by_id['def:fieldextension']['issues'] if i['id'] == 'MS21-DEF-01')
    definition.update(summary='The empty item is gone, but items (iv) and (v) and the closing sentence still define algebraic, finitely generated and separable extensions for κ/K inside a definition about L/K.',
                      fix='Write L/K throughout the definition.')

    def finding(identifier, issue_id, summary, fix, severity='minor'):
        by_id[identifier]['issues'].append(dict(id=issue_id, severity=severity, summary=summary, fix=fix,
                                                aicomment=None, status='open; paper preserved verbatim'))
    finding('further-work', 'MS28-REF-01', 'The paragraph no longer lists the identity in every right Ore localization, but its Lean reference still cites LocalizationCorollaries.s38_rightOreLocalization first.',
            'Restore the consequence or drop the reference.', 'editorial')
    finding('conv:pair', 'MS28-TYPO-01', 'The sentence after the display reads “δ vanishes on A_{n−1}(k). so that x₁ is central in C”: a full stop interrupts the sentence.',
            'Remove the full stop before “so that”.', 'editorial')
    finding('ithm:gabber', 'MS28-FIELD-01', 'The statement is over a field K with A_n(K)-modules, but writes J = √Ann_{k[x,ξ]} gr M with lower-case k.',
            'Write K[x,ξ].', 'editorial')

    # ------------------------------------------------ comparison notes ----
    notes = {
        'thm:main': ('Stafford 3.8 with fixed source F = Φ_g⁻¹(x₁)^{deg_B d}', 'Now stated first as A_n(k) = dA_n(k) + FdA_n(k), then as the equivalent identity 1 = dR + FdS; the “Moreover” clause names F = Φ_g⁻¹(x₁)^{deg_B d} for a linear ω-preserving g as in Section 3. lean-stronger for existence (n ≥ 0 in Lean, n ≥ 1 in the clause); exact for the “Moreover” clause (Lean fixed-source statement for rank n+1, exponent the actual Bernstein degree of d, ℓ = Φ⁻¹(x₁) for a symplectic M with certified inverse).\n\nLean n = 0: rankZero_certificate (UniversalAssembly.lean:38).'),
        'conv:pair': (None, 'Printed as Notation 2.2 (the convention environment now prints “Notation”) and cites Coutinho for the normal form Σ p^j c_j. different-formulation: the Lean normal form is coefficient-left Σ c_j p^j, the paper coefficient-right Σ p^j c_j; both are unique, not termwise equal.\n\nAlgebraicAnalysis file path is in the dependency repo.'),
        'cotangent': ('Cotangent bundle T*X', 'Now Definition 2.5, replacing Subsection 2.1. It defines T*X = X × (k^n)^* with coordinate ring k[x,ξ] = gr A_n(k), regards X and T*X as prime spectra (Definition 2.6) and identifies closed points by Theorem 2.12(a). SymbolRing formalizes the coordinate ring; the projection, fibres and point identification are not mapped to a separate declaration. The hyperplane H is now introduced in Section 5.1.'),
        'def:symplectic-poisson': ('Symplectic forms and the standard form on k^{2n}', 'The October 21 Definition 2.5 is split: this card keeps the symplectic form, now with nondegeneracy, orthogonal complements, symplectic bases and Gram matrices; the Poisson bracket is Definition 2.9. Lean phasePairing(u, v) = Σᵢ (u_{ξᵢ} v_{xᵢ} − u_{xᵢ} v_{ξᵢ}) is −ω; the symplectic group, and with it the normal-form argument, does not depend on the sign.'),
        'def:involutive': (None, 'exact (ideal form). The definition now also calls a closed set W involutive if I(W) is. Lean IsInvolutive uses poissonBracket, which equals the printed bracket (Definition 2.9).\n\nLean IsPoisson (Polynomial.lean:40) is the stronger Poisson-ideal notion, not used for Gabber.'),
        'ithm:gabber': (None, 'Now stated directly for a finitely generated A_n(K)-module with a good order filtration (char K = 0) and cited to Hotta–Takeuchi–Tanisaki Thm. D.3.4; the general filtered-ring form is kept as a source comment. The pinned Lean source proves involutivity of √Ann gr M for M = A_n(k)/I with the quotient order filtration, the case the proof uses; the manuscript cites Gabber and Singh–Kumar.'),
        'thm:nss': (None, 'Now cited (Hartshorne, Atiyah–Macdonald) with three clauses: (a) maximal ideals are the 𝔪_a, identifying K^N and V_K(J) with closed points; (b) the weak form; (c) I(V_K(J)) = √J. Lean uses Mathlib Nullstellensatz and Jacobson-ring results inside the mapped geometric proofs; no separate declaration or new verification receipt is claimed.'),
        'def:good-filtration': (None, 'Now cites Coutinho and spells out the graded-module structure of gr M over gr_F A_n(k). ' + by_id['def:good-filtration']['correspondence']),
        'cor:charP': (None, 'Proposition 3.6, stated with the order filtration induced by the cyclic generator; its proof now follows the statement. Lean: Ann gr Q is the order initial ideal of the canonical right ideal, and the order principal component of the normal form lies in it (canonical_orderPrincipalComponent_mem_initialIdeal).'),
        'lem:tangential-finiteness': (None, 'The proof derives tangential finiteness from the monic quotient, proves kernel-support containment by localized surjectivity and Vasconcelos, and now argues finite length at a minimal support prime: the support of U_𝔮 and V_𝔮 is the maximal ideal, so they are finite over an Artinian quotient (Atiyah–Macdonald Thm. 8.5, Stacks 00L2, 00KH). Lean: localized_kernel_and_cokernel_isFiniteLength.'),
        'lem:strict-support-inequality': (None, 'The proof cites Hotta–Takeuchi–Tanisaki Thm. D.3.4 for involutivity of the minimal primes of J instead of a localization argument, excludes x₁ by iterated brackets, writes k[x,ξ]_𝔮 = S⁻¹k[x,ξ] for S = T∖𝔮 explicitly, and proves strict length positivity using the stable power kernel K_∞ and Nakayama. Lean also proves minimal-prime involutivity (minimalPrime_isInvolutive).'),
        'prop:char-avoids': (None, 'Proposition 6.1 now states Char(Q) ∩ V(x₁) = ∅ in Spec k[x,ξ], with Supp(M/x₁M) = Supp(M) ∩ V(x₁) and Char(Q) = Supp(M) (Stacks 00L2) from Corollary 4.11. The formal support statement is transported along the fibre sign change, which fixes x₁.'),
        'proof-main': (None, 'W is now the set of closed points of Char(Q_K); the avoidance of π⁻¹(H) follows from Proposition 6.1, Lemma 6.2 and Theorem 2.12(a). The exact step-by-step correspondence with the final formal proof source remains pending; the current map retains the historical formal endpoint for orientation only.'),
        'cyclicity': (None, 'Now attributed to Stafford 1978. Selected finite-generation induction uses a common annihilator d₂e and the explicit generator t₁−t₂F. Its certificate calculation also has a separate literal supplementary challenge and trust-zero consumer. Stable cyclicity is now argued in the text: for l = 1 by f₁ = −F for an arbitrary generating pair, for l ≥ 2 by Stafford’s two-generator theorem; it is not separately mapped to a Lean declaration.'),
        'further-work': ('Consequences proved in Lean', 'The first paragraph of Section 7 lists three consequences without printed proofs; each is mapped separately below. The identity in every right Ore localization is no longer listed, although the paragraph’s Lean reference still cites it (MS28-REF-01). The left-handed, localized differential-operator and evolutionary declarations exist at the pinned formal commit.'),
        'appendix-left-handed': (None, 'The paragraph adds that the left-handed identity gives Corollary 6.3 for left torsion modules. ' + by_id['appendix-left-handed']['correspondence']),
        'outlook': ('Open questions and a terminating search', 'Discussion, not a theorem. The fixed choice F = Φ_g⁻¹(x₁)^{deg_B d} gives a terminating search over computable fields; bounds and efficiency remain open. FV-03 marks the citation of generalization (b) as a placeholder.'),
        'context-prior-art': ('Related literature', 'Rewritten: Dixmier and Stafford on two-generator results, algorithms by Hillebrand–Schmale, Leykin and Caro–Levcovitz, Stafford’s statement of Conjecture 3.8 and its consequence for stable cyclicity, Leykin’s holonomic cyclicity, and the textbooks the proof relies on. Literature context, not a claim that the cited work proves Conjecture 3.8.'),
        'formal-verification': (None, 'The subsection states that Theorem 1.1 and Corollary 6.3 are proved in Lean from the three standard axioms, and that every intermediate result is proved as well, along Sections 3–6. The reader maps the formal counterparts card by card; several printed lemmas (for example Lemmas 4.7, 5.9 and 5.13) have no exact Lean declaration mapped here, their content being used inside larger formal results.'),
        'thm:asymptotic-conormal-proof': ('Proof of the asymptotic conormal theorem', 'Subsection 5.2: an algebraic case, a valuation ring and discrete valuation ring at infinity (Lemmas 5.9, 5.10), residue-field differentials (Lemma 5.11, now proved via a differential basis, Matsumura Thm. 26.5), the Laurent generic tangent cone (Lemma 5.12), a unit minor, and lifting the 1-coordinate row (Lemma 5.13). Most cited sources are now pinned to textbook statements. The formal endpoint still assembles the retained SameWitness route; matching conclusions do not certify this printed proof step by step.'),
        'lem:kappa': (None, 'A subset of the residues q_i(0) with i ∉ {0,1,j} gives a basis of Ω_{κ/K}. The proof now takes a transcendence basis of L/K (Lang Thm. VIII.1.1), shows it is one of κ/K, and cites Matsumura Thm. 26.5 for the differential basis in characteristic zero instead of extending derivations by hand. The cited formal result supports the differential span argument; it does not certify the printed basis statement by itself.'),
        'thm:coisotropic-exclusion-proof': ('Proof of the involutive exclusion theorem', 'Subsection 5.3. It establishes fibre homogeneity, the zero section over the projected base Y = V_K(B), Hamiltonian translations (now citing Hotta–Takeuchi–Tanisaki Ch. E.2) and component conormal containment with the conormal space of Definition 5.4, then applies Theorem 5.7. The theorem is stated contrapositively (W must be empty).'),
        'ai-workflow': (None, 'Rewritten and shortened: the appendix describes the general evolution of the work, the role of AI agents in discovery, review, formalization and writing, and the local models used. ' + by_id['ai-workflow']['correspondence']),
    }
    for identifier, (title, note) in notes.items():
        if title:
            by_id[identifier]['title'] = title
        by_id[identifier]['correspondence'] = note
    sym = by_id['def:symplectic-poisson']
    sym['lean'] = [r for r in sym['lean'] if not r['name'].endswith('.poissonBracket')]
    by_id['def:involutive']['depends_on'] = ['def:poisson']
    by_id['thm:asymptotic-conormal']['depends_on'] = ['def:valuation', 'def:conormal', 'lem:W', 'lem:place',
                                                       'lem:kappa', 'lem:tangent', 'lem:ell']
    by_id['dir-def']['depends_on'] = ['def:conormal']
    by_id['cyclicity']['depends_on'] = ['def:cyclic', 'thm:main']

    # ------------------------------------------------- source and texts ----
    tie_order = {'challenge-main': 1, 'challenge-fixed-source': 2}
    items.sort(key=lambda i: (i['tex_lines'][0], tie_order.get(i['id'], 0)))
    source = dict(repo='itpplasma/stafford38-paper', commit=commit, file='human_readable_main.tex',
                  origin_repo='itpplasma/stafford38-paper', origin_commit=commit,
                  sha256=hashlib.sha256(raw.encode()).hexdigest(), label='Paper (Overleaf update)',
                  local_source_base='./sources/paper',
                  note='October 28 Overleaf update, preserved verbatim.')
    snapshot_files = {}
    snapshot_base = ROOT / 'sources/paper/raw'
    snapshot_base.mkdir(parents=True, exist_ok=True)
    for file in ['human_readable_main.tex', 'references.bib', 'ai_review.tex']:
        content = git(paper, 'show', f'{commit}:{file}')
        (snapshot_base / file).write_text(content)
        snapshot_files[file] = hashlib.sha256(content.encode()).hexdigest()
    source['snapshot'] = dict(base='sources/paper/raw', files=snapshot_files)
    open_findings = sorted(i['id'] for item in items for i in item['issues'] if i['id'].startswith('MS'))
    mapping['version'] = '0.2.6-manuscript-review'
    mapping['subtitle'] = 'October 28 manuscript · paper and Lean proof comparison'
    mapping['reader_notice'] = f'Manuscript updated 28 October 2026. {len(open_findings)} review findings are recorded under Comparison notes.'
    mapping['sources']['paper'] = source
    mapping['items'] = items
    mapping['aicomments'] = [dict(id=m[1], line=line_at(m.start()), verdict='author review pending',
        note='Active annotation in the updated manuscript; no author acceptance is inferred.')
        for m in re.finditer(r'\\AIcomment\{([^{}]+)\}', clean)]
    mapping['provenance'] = '<p>The paper passages are the October 28 Overleaf update, pinned and reproduced verbatim. The formal source pins and historical verification receipts are retained. Mathematical edits to the manuscript have not been made by this supplementary update. Comparison labels do not certify a revised printed proof.</p>'
    mapping['comparison_scope'] = 'The active October 28 manuscript, including visible AI markup. Unchanged Lean source pins retain their previous verification scope; updated printed proofs require fresh human correspondence review.'
    mapping['overview'] = 'Compare the October 28 Overleaf manuscript with the pinned Lean results. The new preliminary definitions of Sections 2 and 5, the renumbered conormal lemmas and the two generalizations of Section 7 are represented explicitly. The selected formal endpoint still follows its recorded SameWitness route; matching conclusions do not certify the revised printed proof step by step. Johanna’s author review and Max’s correspondence review remain pending.'
    mapping['candidate']['status'] = 'October 28 manuscript refresh; formal source pins unchanged; human correspondence review pending'
    mapping['candidate']['manuscript'] = source
    manifest['version'] = mapping['version']
    manifest['sources'] = mapping['sources']
    manifest['review'].update(claims=len(items), scope=mapping['comparison_scope'],
        statement_relations=dict(collections.Counter(i['statement_relation'] for i in items)),
        proof_routes=dict(collections.Counter(i['route_relation'] for i in items)))
    manifest['status'] = 'manuscript-update-in-progress'
    manifest['checks'] = dict(status='pending', receipt='verification/manuscript-20261028/verification.json',
        note='Historical checks remain in their original receipts; they do not verify the updated manuscript build.')
    manifest['manuscript_pdfs']['current_paper_commit'] = commit
    manifest['manuscript_pdfs']['paper_pdf_status'] = 'rebuild-required'

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
    old_ids = {i['id'] for i in json.loads(git(ROOT, 'show', f'{base_rev}:paper-lean-map.json'))['items']}
    if git(paper, 'status', '--porcelain=v1') != before:
        raise SystemExit('Paper worktree changed during migration')
    history = dict(base_supplementary_revision=base_rev, previous_paper=old_source, current_paper=source,
                   renamed_labels={'sec:cotangent': 'def:cotangent', 'def:symplectic-poisson': 'def:symplectic'},
                   deleted_labels=DELETED_LABELS, renumbered_statements={k: v for k, v in renumber.items() if k != v},
                   removed_cards=sorted(old_ids - set(by_id)), added_cards=sorted(set(by_id) - old_ids),
                   active_statements=len(statements), current_cards=len(items),
                   open_findings=open_findings, expected_unresolved_refs=[],
                   expected_unresolved_citations=[],
                   paper_worktree_status_before=before,
                   note='The paper repository is read-only throughout this migration.')
    assert history['removed_cards'] == sorted(REMOVED)
    RECEIPT.mkdir(parents=True, exist_ok=True)
    (RECEIPT / 'migration.json').write_text(json.dumps(history, indent=2, ensure_ascii=False) + '\n')
    for name, value in [('paper-lean-map.json', mapping), ('manifest.json', manifest)]:
        (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    print(f'Pinned manuscript {commit[:12]}; {len(items)} cards ({len(history["added_cards"])} added, '
          f'{len(history["removed_cards"])} removed); {len(statements)} active statements; '
          f'{len(open_findings)} open findings. Paper unchanged.')


if __name__ == '__main__':
    main()
