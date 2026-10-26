#!/usr/bin/env python3
"""Map the reader to the October 21 manuscript layout without editing the paper.

The October 21 Overleaf update restructured the paper: a Lean subsection in
the introduction, the vanishing-cokernel and characteristic-variety material
merged into Sections 3 and 4, the conormal geometry rewritten as Section 5
with nested lemmas, and the Outlook and Further work replaced by
"Generalizations and open questions". update-manuscript.py records the
October 18 migration and is kept unchanged for reproducibility.

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
RECEIPT = ROOT / 'verification/manuscript-20261021'
_spec = importlib.util.spec_from_file_location('update_manuscript', ROOT / 'scripts/update-manuscript.py')
um = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(um)
git, active_tex, environments = um.git, um.active_tex, um.environments

# Card ids are kept stable (they key saved review notes); labels follow the paper.
RENAMED = {'cor:charP': 'prop:charP', 'lem:Uzero': 'cor:Uzero'}
# Labelled statements of the October 18 source that no longer exist. All of
# them were already inside comment environments there and had no card.
DELETED_COMMENTED = ['def:conormal', 'def:divisorial', 'def:proj-closure',
                     'def:smooth-conormal', 'lem:lift', 'lem:special']
SECTIONS = [
    ('1', 'Introduction', None), ('1.1', 'Related literature', None),
    ('1.2', 'Formal verification with Lean', 'sec:formal'),
    ('2', 'Preliminaries', 'sec:setting'),
    ('2.1', 'Cotangent space and symplectic structure', 'sec:cotangent'),
    ('3', 'Mapping to a normal form', 'sec:monic'),
    ('4', 'x\u2081 as a surjective map', 'sec:euler'),
    ('5', 'Avoiding the hyperplane {x\u2081 = 0}', 'sec:conormal-review'),
    ('5.1', 'Definitions', 'sub:def_geom'),
    ('5.2', 'Proof of Theorem 5.5', 'sub:asym'),
    ('5.3', 'Proof of Theorem 5.6', 'sub:excl'),
    ('6', 'Proof of Theorem 1.1', 'sec:proof'),
    ('7', 'Generalizations and open questions', 'sec:generalizations'),
    ('A', 'Appendix A: AI-assisted research and formalization', 'app:ai-workflow'),
]


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
    kinds = set(re.findall(r'\\newtheorem\{([^{}]+)\}', clean))
    statements = []
    for name, start, end in envs:
        if name in kinds:
            found = re.search(r'\\label\{([^{}]+)\}', clean[start:end])
            statements.append((name, found[1] if found else None, line_at(start), line_at(end)))
    unlabelled = [s for s in statements if not s[1]]
    if unlabelled:
        raise ValueError(f'Unlabelled statements need a card id: {unlabelled}')
    heads = [(line_at(m.start()), m[1]) for m in
             re.finditer(r'\\(section|subsection)\{', clean)]
    section_lines = [a for a, kind in heads if kind == 'section']
    bounds = [a for a, _ in heads] + [len(lines) + 1]
    proofs = [(line_at(a), line_at(b)) for n, a, b in envs if n == 'proof']

    mapping = json.loads(git(ROOT, 'show', f'{base_rev}:paper-lean-map.json'))
    manifest = json.loads(git(ROOT, 'show', f'{base_rev}:manifest.json'))
    old_source = mapping['sources']['paper']
    if old_source['commit'] == commit:
        raise SystemExit('Base revision is already migrated; pass --base-rev of the October 18 map')
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
        'cotangent': [labels['sec:cotangent'], labelled_range('def:good-filtration')[0] - 1],
        'monic-scalar': [line_of(r'If $N=0$'), line_of(r'We want to construct a well-behaved') - 1],
        'phi-g': [line_of(r'Let $g$ be a $k$-linear automorphism'), labelled_range('prop:monic')[0] - 1],
        'eq:I-Q': [line_of(r'We will now define the modules'), line_of(r'We now use the order filtration') - 1],
        'euler-grading': [labels['sec:euler'] + 1, labelled_range('lem:euler')[0] - 1],
        'vc-setup': [line_of(r'For this part, we write $M='), labelled_range('lem:tangential-finiteness')[0] - 1],
        'thm:asymptotic-conormal-proof': [labels['sub:asym'], labels['sub:excl'] - 1],
        'proof-main': [line_of(r'Let $d\in A_n(k)$ be nonzero of Bernstein degree'), labelled_range('cor:cyclic')[0] - 1],
        'further-work': [gen, line_of(r'\AIadd{Two further results') - 1],
        'appendix-right-ore': [line_of('the identity in every right Ore', gen), line_of('the left-handed identity', gen)],
        'appendix-left-handed': [line_of('the left-handed identity', gen), line_of('formal adjoint; the identity for finite-order', gen)],
        'appendix-localized-differential': [line_of('formal adjoint; the identity for finite-order', gen), line_of('of the geometric argument, the identity', gen) - 1],
        'appendix-evolutionary': [line_of('of the geometric argument, the identity', gen) - 1, line_of('provided each $a_j$ commutes', gen)],
        'global-stafford': [line_of(r'\item Let $A$ be a smooth'), line_of(r'\item Let $U$ be an infinite') - 1],
        'outlook': [line_of(r'The proof of Theorem~\ref{thm:main} shows $Q=0$'), line_of(r'\clearpage') - 1],
        'ai-workflow': [labels['app:ai-workflow'], line_of(r'\end{appendix}') - 1],
    }
    for identifier, value in ranges.items():
        by_id[identifier]['tex_lines'] = value
    by_id['euler-grading']['label'] = 'eq:nonnegative-pbw'
    by_id['eq:I-Q']['label'] = 'eq:I-Q'

    # ------------------------------------------------------- new cards ----
    def add(identifier, title, label=None, tex_lines=None, kind=None, refs=(),
            relation='partial', route='n/a', note='', short=None):
        if label:
            kind = next(s[0].title() for s in statements if s[1] == label)
            tex_lines = tex_lines or labelled_range(label)
        item = dict(id=identifier, section='', kind=kind, number='', short=short or title,
                    title=title, tex_lines=tex_lines, statement_relation=relation,
                    route_relation=route, correspondence=note, route=None, lean=list(refs),
                    depends_on=[], in_graph=False, graph_sub=None, graph_order=0,
                    auditors=[], review_scope='publication', historical_issues=[], issues=[])
        if label:
            item['label'] = label
        items.append(item)
        by_id[identifier] = item

    def ref(file, name, repo='formal', role='supporting result'):
        return dict(file=file, name=name, repo=repo, role=role)

    add('def:fieldextension', 'Algebraic and transcendental elements; transcendence bases',
        label='def:fieldextension', note='Standard field-theory vocabulary used by the conormal argument. Lean uses the Mathlib notions (algebraicity, transcendence, transcendence bases); no separate formal theorem is claimed for this definition.')
    add('def:omega', 'Derivations and Kähler differentials of a field extension',
        label='def:omega', note='Standard construction of the differentials of a field extension and their duality with derivations. Lean uses Mathlib Kähler differentials; no separate formal theorem is claimed for this definition.')
    add('lem:W', 'A valuation ring at infinity in which x̄₁ vanishes', label='lem:W', route='similar',
        note='New lemma: a valuation ring dominating K[x̄₁] localized at x̄₁ and a homogeneous chart index. The Lean annotation after the theorem proof covers the divisorial frame collectively; a declaration proving exactly this printed lemma is not asserted here.')
    add('lem:ell', 'Annihilators of the tangent cone are conormal', label='lem:ell', route='similar', refs=[
        ref('Stafford38/Geometry/PaperActualWitnessConormalData.lean', 'Stafford38.Geometry.PaperActualWitnessConormalData.exists_regularizedOneRowConormalData_of_actual_witness')],
        note='New lemma: a row vector annihilating the homogeneous tangent cone gives an affine conormal covector. The cited declaration from the theorem annotation is the closest formal counterpart (conormal row data for the witness); its hypotheses have not been compared clause by clause.')
    p_start = proofs[[i for i, p in enumerate(proofs) if p[0] > labels['sec:proof']][0]][0]
    add('prop:charP-proof', 'Proof of Proposition 3.6 (printed at the start of Section 6)', kind='Proof',
        tex_lines=[p_start, labelled_range('prop:char-avoids')[0] - 1], relation='n/a', route='similar', short='Proof of 3.6',
        refs=[ref('Stafford38/Characteristic/InitialIdeal.lean', 'Stafford38.CharacteristicInitialIdeal.canonical_orderPrincipalComponent_mem_initialIdeal')],
        note='The proof that the order symbol P annihilates gr Q is printed at the start of Section 6, before the proposition on support avoidance, rather than after Proposition 3.6. Lean proves membership of the order principal component in the order initial ideal.')
    by_id['prop:charP-proof']['depends_on'] = ['cor:charP']
    excl = labels['sub:excl']
    add('thm:coisotropic-exclusion-proof', 'Proof of the involutive exclusion theorem', kind='Proof',
        tex_lines=[excl, labels['sec:proof'] - 1], relation='n/a', route='same', short='Proof of 5.6',
        refs=[ref('Stafford38/Geometry/GeneralCoisotropicExclusion.lean', 'Stafford38.Geometry.GeneralCoisotropicExclusion.exists_zero_base_coordinate'),
              ref('Stafford38/Geometry/GeneralComponentConormalContainment.lean', 'Stafford38.Geometry.GeneralComponentConormalContainment.equationConormalClosure_minimalPrime_subset_zeroLocus'),
              ref('Stafford38/Geometry/GeneralAsymptoticConormal.lean', 'Stafford38.Geometry.GeneralAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure')],
        note='The proof now has its own subsection after both theorem statements. It establishes fibre homogeneity, the zero section over the projected base, Hamiltonian translations and component conormal containment, then applies the asymptotic conormal theorem. The theorem is stated contrapositively (W must be empty), which is equivalent to the October 18 form.')
    by_id['thm:coisotropic-exclusion-proof']['depends_on'] = ['thm:coisotropic-exclusion', 'thm:asymptotic-conormal']
    add('conormal-intro', 'Section 5 overview', kind='Paragraph', short='Section 5',
        tex_lines=[labels['sec:conormal-review'], labels['sub:def_geom'] - 1], relation='n/a',
        note='Section overview; it names the two main results and where they are proved. No formal claim.')
    add('generalization-filtered', 'Generalization (b): filtered simple algebras', kind='Paragraph',
        short='Generalization (b)', tex_lines=[line_of(r'\item Let $U$ be an infinite'), line_of(r'\end{enumerate}', gen)],
        relation='equivalent', refs=[
            ref('Challenge.lean', 'SymplecticStaffordChallenge.AffineSameDivisorStatement', 'filtered', 'statement'),
            ref('Solution.lean', 'SymplecticStaffordChallenge.universalStatement', 'filtered', 'statement')],
        note='Lean states the identity 1 = dR + (B + Ha)dS for a simple, infinite-dimensional k-algebra U with an exhaustive, multiplicative filtration by finite-dimensional pieces, F₀U = k, whose associated graded ring is a commutative, finitely generated domain encoded by graded symbol maps. Lean additionally assumes finite Krull dimension of the graded ring, which holds for every finitely generated commutative k-algebra. The paper gives no printed proof; the manuscript marks the citation as a placeholder (AI comment FV-03).')
    mapping['sources']['filtered'] = dict(
        repo='itpplasma/symplectic-stafford-formal', commit='dccff0d8fe723ec1478d1f63bbbdf648ba240bfa',
        note='Generalization (b) of Section 7, at the revision linked by the manuscript (\\leanfilteredrepo).',
        file='Solution.lean', name='SymplecticStaffordChallenge.universalStatement')

    # ------------------------------------------- sections and numbering ----
    sec_line = {number: (labels[label] if label else None) for number, _, label in SECTIONS}
    sec_line['1'] = line_of(r'\section{Introduction}')
    sec_line['1.1'] = line_of(r'\subsection{Related literature}')
    ordered = sorted((line, number) for number, line in sec_line.items())
    mapping['sections'] = [dict(number=n, title=t, **({'label': l} if l else {})) for n, t, l in SECTIONS]
    for item in items:
        start = item['tex_lines'][0]
        item['section'] = ([n for line, n in ordered if line <= start] or ['1'])[-1]
    counts, numbered = collections.Counter(), {}
    for kind, label, a, b in statements:
        sec = str(sum(start <= a for start in section_lines))
        counts[sec] += 1
        numbered[label] = f'{sec}.{counts[sec]}'
    for item in items:
        if item.get('label') in numbered:
            item['number'] = numbered[item['label']]
            item['kind'] = next(s[0].title() for s in statements if s[1] == item['label'])
            item['short'] = f"{item['kind']} {item['number']}"
        for step in item.get('steps', []):
            step.pop('tex_lines', None)
    assert numbered['thm:asymptotic-conormal-formal'] == '5.5' and numbered['thm:coisotropic-exclusion'] == '5.6'
    shorts = {'formal-verification': 'Section 1.2', 'proof-main': 'Proof §6',
              'thm:asymptotic-conormal-proof': 'Proof of 5.5', 'further-work': 'Section 7',
              'global-stafford': 'Generalization (a)', 'outlook': 'Section 7', 'ai-workflow': 'Appendix A',
              'intro-proof-sketch': 'Proof sketch §1', 'vc-setup': 'Setup §4', 'context-prior-art': 'Section 1.1'}
    for identifier, short in shorts.items():
        by_id[identifier]['short'] = short
    # Subsection and equation numbers of passage cards, checked against the
    # isolated paper build's .aux file.
    for identifier, kind, number in [
            ('cotangent', 'Subsection', '2.1'), ('eq:I-Q', 'Equation', '3.2'),
            ('euler-grading', 'Paragraph', ''), ('formal-verification', 'Subsection', '1.2'),
            ('thm:asymptotic-conormal-proof', 'Proof', 'of 5.5'),
            ('thm:coisotropic-exclusion-proof', 'Proof', 'of 5.6'), ('prop:charP-proof', 'Proof', 'of 3.6'),
            ('proof-main', 'Proof', '§6'), ('further-work', 'Section', '7'), ('outlook', 'Paragraph', '')]:
        by_id[identifier].update(kind=kind, number=number)

    # ------------------------------------------------ comparison notes ----
    notes = {
        'formal-verification': ('Formal verification with Lean', 'The new subsection states that Theorem 1.1 with F = ℓ^{deg_B d} and Corollary 6.3 are proved in Lean from the three standard axioms, and that every intermediate result is proved as well, along Sections 3–6. The reader maps the formal counterparts card by card; several printed lemmas (for example Lemmas 4.7, 5.7 and 5.11) have no exact Lean declaration mapped here, their content being used inside larger formal results.'),
        'cor:charP': ('P annihilates gr Q', 'Now Proposition 3.6, stated with the order filtration induced by the cyclic generator. Lean: Ann gr Q is the order initial ideal of the canonical right ideal, and the symbol of the normal form lies in it. The printed proof is separated from the statement (see the proof card in Section 6).'),
        'lem:Uzero': ('gr Q = (gr Q)x₁', 'Now Corollary 4.11 with a short proof by contradiction from Lemmas 4.8–4.10 at a minimal support prime. Lean localizes both inequalities at q.asIdeal.primeCompl in T k n = MvPolynomial (Fin n ⊕ Fin n) k, q minimal in Supp_T(U).'),
        'prop:char-avoids': (None, 'Now Proposition 6.1 with a single proof: Supp(M/x₁M) = Supp(M) ∩ V(x₁) and Corollary 4.11. The duplicate proof of October 18 is gone. The formal support statement is transported along the fibre sign change, which fixes x₁.'),
        'lem:place': (None, 'Rewritten: from the valuation ring of Lemma 5.7 the proof builds a discrete valuation ring with all qᵢ in V, x̄₁ in the maximal ideal, R ⊄ V, residue field algebraic over the residues of q, and finitely generated Ω_{V/K}. The cited formal result supplies a divisorial visible frame with residue algebraicity; an exact wrapper for every clause is not claimed.'),
        'lem:kappa': (None, 'Rewritten: a subset of the residues q_i(0) with i ∉ {0,1,j} gives a basis of Ω_{κ/K}, with dual derivations. The vanishing q₀(0) = q₁(0) = 0 is now established before the lemma. The cited formal result supports the differential span argument; it does not certify the printed basis statement by itself.'),
        'lem:tangent': (None, 'Rewritten with two clauses: the dimension bound for the tangent space and cone, and membership of δq(t) and q(t) in the cone. The dimension bound has a named formal analogue for the retained witness; the membership clause requires its own comparison.'),
        'thm:asymptotic-conormal-proof': (None, 'The proof is now Subsection 5.2: an algebraic case, a valuation ring and discrete valuation ring at infinity (Lemmas 5.7, 5.8), residue-field differentials (Lemma 5.9), the Laurent generic tangent cone (Lemma 5.10), a unit minor, and lifting the x₁-row (Lemma 5.11). The October 18 commented-out closed-point proof has been deleted from the source. The formal endpoint still assembles the retained SameWitness route; matching conclusions do not certify this printed proof step by step.'),
        'thm:coisotropic-exclusion': (None, 'Now stated contrapositively: a closed, fibre-conical, involutive W on which P vanishes and which avoids π⁻¹(H) is empty. This is equivalent to the October 18 form. Lean allows any algebraically closed characteristic-zero field and any P with P(1,0,…,0) ≠ 0, not necessarily homogeneous. The proof is a separate card.'),
        'cyclicity': (None, 'Selected finite-generation induction uses a common annihilator d₂e and the explicit generator t₁−t₂F. Its certificate calculation also has a separate literal supplementary challenge and trust-zero consumer. The proof now adds a stable-cyclicity paragraph with a pending AI completion (CYC-01); stable cyclicity is not separately mapped to a Lean declaration.'),
        'global-stafford': ('Generalization (a): differential operators on smooth affine domains', 'Item (a) of Section 7 states the identity for D_k(A), A a smooth finitely generated k-algebra that is a domain. It is proved in the separate pinned repository itpplasma/global-stafford-formal at v1.0.6; the paper distinguishes existence of F from the fixed linear-coordinate choice of Theorem 1.1.'),
        'further-work': ('Consequences proved in Lean', 'The first paragraph of Section 7 lists four consequences without printed proofs; each is mapped separately below. The localization, left-handed, localized differential-operator and evolutionary declarations exist at the pinned formal commit.'),
        'outlook': ('Open questions and a terminating search', 'Discussion, not a theorem. A pending AI replacement (ALG-05) says the fixed choice of F gives a terminating search over computable fields; bounds and efficiency remain open. FV-03 marks the citation of generalization (b) as a placeholder.'),
        'eq:I-Q': (None, 'The canonical right ideal and quotient are now defined in Section 3, after Remark 3.3. Lean Euler element is θ = x·p, same as the paper E = x₁p; Weyl relation p·x = x·p + 1 (pairMomentum_mul_coordinate, Stafford38/Ore/PairStage.lean:80).'),
    }
    for identifier, (title, note) in notes.items():
        if title:
            by_id[identifier]['title'] = title
        by_id[identifier]['correspondence'] = note
    by_id['thm:asymptotic-conormal']['depends_on'] = ['lem:W', 'lem:place', 'lem:kappa', 'lem:tangent', 'lem:ell']
    by_id['lem:place']['depends_on'] = ['lem:W']

    # ---------------------------------------------------------- findings ----
    resolved = {
        'formal-verification': 'MS18-REF-01', 'prop:char-avoids': 'MS18-DUP-01', 'lem:kappa': 'MS18-ORDER-01'}
    for identifier, issue_id in resolved.items():
        issue = next(i for i in by_id[identifier]['issues'] if i['id'] == issue_id)
        issue['status'] = f'resolved in paper {commit[:7]}'
        by_id[identifier]['issues'].remove(issue)
        by_id[identifier]['historical_issues'].append(issue)
    # Proposed changes whose AI comments were removed from the manuscript.
    for identifier in ['further-work']:
        for issue in [i for i in by_id[identifier]['issues'] if i.get('aicomment') in {'REF-01', 'SCOPE-01'}]:
            issue['status'] = f'AI comment no longer in the manuscript at {commit[:7]}'
            by_id[identifier]['issues'].remove(issue)
            by_id[identifier]['historical_issues'].append(issue)
    carried = next(i for i in by_id['thm:coisotropic-exclusion']['issues'] if i['id'] == 'MS18-REF-02')
    by_id['thm:coisotropic-exclusion']['issues'].remove(carried)
    carried.update(summary='The proof of Theorem 5.6 still references def:conormal, which no longer exists in the source; the compiled paper prints “Definition ??”.',
                   fix='Restore the conormal-space definition or replace the reference.')
    notation = by_id['lem:strict-support-inequality']['issues'][0]
    notation.update(summary='The radical annihilator is now named J, but the proof still writes p_p = I_p once, and localizes Ann over k[x,ξ]_p while M is localized at the tangential prime q.',
                    fix='Use J throughout and clarify the commutative symbol ring and localization maps.')

    def finding(identifier, issue_id, summary, fix, severity='minor'):
        by_id[identifier]['issues'].append(dict(id=issue_id, severity=severity, summary=summary, fix=fix,
                                                aicomment=None, status='open; paper preserved verbatim'))
    by_id['thm:coisotropic-exclusion-proof']['issues'].append(carried)
    finding('conormal-intro', 'MS21-CITE-01', 'The section overview cites the undefined bibliography key idk; the compiled paper prints “[?]”.',
            'Replace the placeholder citation with an algebraic-geometry textbook.')
    finding('intro-proof-sketch', 'MS21-TODO-01', 'The proof sketch begins “We start in section XXX”.', 'Replace XXX by Section 3.', 'editorial')
    finding('cor:charP', 'MS21-PROOF-01', 'Proposition 3.6 has no adjacent proof; its proof environment is printed at the start of Section 6, before Proposition 6.1, without a heading naming the proposition.',
            'Move the proof after Proposition 3.6 or label it as its proof.')
    finding('lem:kappa', 'MS21-KAPPA-01', 'Lemma 5.9 states indices i₁,…,i_d but then writes q_{i_r}; the proof leaves “which defines d′ = ” unfinished; the preceding text writes q₀(t) = q₁(0) = 0 for q₀(0) = q₁(0) = 0.',
            'Use one name for the transcendence degree of L/K and complete the sentence.')
    finding('thm:asymptotic-conormal-proof', 'MS21-REF-03', 'The proof cites Lemma 5.10(c) for annihilators of the tangent cone; Lemma 5.10 now has only clauses (a) and (b), and the statement used is Lemma 5.11.',
            'Cite Lemma 5.11.')
    finding('def:fieldextension', 'MS21-DEF-01', 'The enumeration contains “\\item \\item”, which prints an empty item, and clause (iii) defines κ/K inside a definition about L/K.',
            'Remove the duplicate \\item and write L/K.', 'editorial')

    # ------------------------------------------------- source and texts ----
    tie_order = {'challenge-main': 1, 'challenge-fixed-source': 2}
    items.sort(key=lambda i: (i['tex_lines'][0], tie_order.get(i['id'], 0)))
    source = dict(repo='itpplasma/stafford38-paper', commit=commit, file='human_readable_main.tex',
                  origin_repo='itpplasma/stafford38-paper', origin_commit=commit,
                  sha256=hashlib.sha256(raw.encode()).hexdigest(), label='Paper (Overleaf update)',
                  local_source_base='./sources/paper',
                  note='October 21 Overleaf update, preserved verbatim.')
    snapshot_files = {}
    snapshot_base = ROOT / 'sources/paper/raw'
    snapshot_base.mkdir(parents=True, exist_ok=True)
    for file in ['human_readable_main.tex', 'references.bib', 'ai_review.tex']:
        content = git(paper, 'show', f'{commit}:{file}')
        (snapshot_base / file).write_text(content)
        snapshot_files[file] = hashlib.sha256(content.encode()).hexdigest()
    source['snapshot'] = dict(base='sources/paper/raw', files=snapshot_files)
    open_findings = sorted(i['id'] for item in items for i in item['issues'] if i['id'].startswith('MS'))
    mapping['version'] = '0.2.5-manuscript-review'
    mapping['subtitle'] = 'October 21 manuscript · paper and Lean proof comparison'
    mapping['reader_notice'] = f'Manuscript updated 21 October 2026. {len(open_findings)} review findings are recorded under Comparison notes.'
    mapping['sources']['paper'] = source
    mapping['items'] = items
    mapping['aicomments'] = [dict(id=m[1], line=line_at(m.start()), verdict='author review pending',
        note='Active annotation in the updated manuscript; no author acceptance is inferred.')
        for m in re.finditer(r'\\AIcomment\{([^{}]+)\}', clean)]
    mapping['provenance'] = '<p>The paper passages are the October 21 Overleaf update, pinned and reproduced verbatim. The formal source pins and historical verification receipts are retained. Mathematical edits to the manuscript have not been made by this supplementary update. Comparison labels do not certify a revised printed proof.</p>'
    mapping['comparison_scope'] = 'The active October 21 manuscript, including visible AI markup. Unchanged Lean source pins retain their previous verification scope; updated printed proofs require fresh human correspondence review.'
    mapping['overview'] = 'Compare the October 21 Overleaf manuscript with the pinned Lean results. The restructured conormal section, its new lemmas and the two generalizations of Section 7 are represented explicitly. The selected formal endpoint still follows its recorded SameWitness route; matching conclusions do not certify the revised printed proof step by step. Johanna’s author review and Max’s correspondence review remain pending.'
    mapping['candidate']['status'] = 'October 21 manuscript refresh; formal source pins unchanged; human correspondence review pending'
    mapping['candidate']['manuscript'] = source
    manifest['version'] = mapping['version']
    manifest['sources'] = mapping['sources']
    manifest['generator'] = dict(repo='itpplasma/paper-lean-audit',
        commit='32c720bb20d7bf8744a75c9f556529077d00db16', version='manuscript-20261021',
        base_commit=manifest['generator']['base_commit'],
        bundle='verification/manuscript-20261021/generator.bundle')
    manifest['review'].update(claims=len(items), scope=mapping['comparison_scope'],
        statement_relations=dict(collections.Counter(i['statement_relation'] for i in items)),
        proof_routes=dict(collections.Counter(i['route_relation'] for i in items)))
    manifest['status'] = 'manuscript-update-in-progress'
    manifest['checks'] = dict(status='pending', receipt='verification/manuscript-20261021/verification.json',
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
    old_ids = {i['id'] for i in json.loads(git(ROOT, 'show', f'{base_rev}:paper-lean-map.json'))['items']}
    if git(paper, 'status', '--porcelain=v1') != before:
        raise SystemExit('Paper worktree changed during migration')
    history = dict(base_supplementary_revision=base_rev, previous_paper=old_source, current_paper=source,
                   renamed_labels=RENAMED, deleted_commented_statements=DELETED_COMMENTED,
                   removed_cards=sorted(old_ids - set(by_id)), added_cards=sorted(set(by_id) - old_ids),
                   active_statements=len(statements), current_cards=len(items),
                   open_findings=open_findings, expected_unresolved_refs=['def:conormal'],
                   expected_unresolved_citations=['idk'],
                   paper_worktree_status_before=before,
                   note='The paper repository is read-only throughout this migration.')
    RECEIPT.mkdir(parents=True, exist_ok=True)
    (RECEIPT / 'migration.json').write_text(json.dumps(history, indent=2, ensure_ascii=False) + '\n')
    for name, value in [('paper-lean-map.json', mapping), ('manifest.json', manifest)]:
        (ROOT / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')
    print(f'Pinned manuscript {commit[:12]}; {len(items)} cards ({len(history["added_cards"])} added, '
          f'{len(history["removed_cards"])} removed); {len(statements)} active statements; '
          f'{len(open_findings)} open findings. Paper unchanged.')


if __name__ == '__main__':
    main()
