#!/usr/bin/env python3
"""Map the reader to the November 2 frozen manuscript without editing the paper.

The frozen version changes only prose: Section 1.2 now says that the proof in
Sections 3-6 follows the formal proof step by step and marks where the routes
differ, and the AI appendix describes how the paper proof was rewritten from
the checked Lean proof. No statement is added, removed or renumbered, so every
card keeps its id, label and number; excerpt ranges are recomputed for the new
source. Section 5.2 is remapped to the Lean module Stafford38.Paper.Section5,
which states Theorem 5.7 and Lemmas 5.9-5.13 as printed. The earlier
update-manuscript*.py scripts are kept unchanged for reproducibility.

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

ROOT = Path(__file__).resolve().parent.parent
RECEIPT = ROOT / 'verification/manuscript-20261102'
VERSION = '0.2.7-manuscript-review'
UPDATED = '2026-11-02'
_spec = importlib.util.spec_from_file_location('update_manuscript', ROOT / 'scripts/update-manuscript.py')
um = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(um)
git, active_tex, environments = um.git, um.active_tex, um.environments


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


def card_ranges(raw, items):
    """Excerpt range of every card in this source, by the rules of the October 28 layout."""
    clean = active_tex(raw)
    lines = clean.split('\n')
    envs = environments(clean)
    line_at = lambda pos: clean.count('\n', 0, pos) + 1
    labels = {m[1]: line_at(m.start()) for m in re.finditer(r'\\label\{([^{}]+)\}', clean)}
    statements, numbered = statement_numbers(clean, line_at)
    heads = [line_at(m.start()) for m in re.finditer(r'\\(section|subsection)\{', clean)]
    bounds = heads + [len(lines) + 1]
    proofs = [(line_at(a), line_at(b)) for n, a, b in envs if n == 'proof']

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

    def labelled_range(label):
        _, _, a, b = next(s for s in statements if s[1] == label)
        if [p for p in proofs if p[0] < a <= p[1]]:
            # Lemmas stated inside a longer proof: the statement and its own proof.
            own = [p for p in proofs if b < p[0] <= b + 2]
            return [a, own[0][1] if own else b]
        limit = min([s[2] - 1 for s in statements if s[2] > b] + [next_bound(a)])
        if label == 'lem:base-change':
            limit = line_of(r'Let $d\in A_n(k)$ be nonzero of Bernstein degree') - 1
        return [a, limit]

    result = {}
    for item in items:
        if item.get('label') and any(s[1] == item['label'] for s in statements):
            result[item['id']] = labelled_range(item['label'])
    gen = labels['sec:generalizations']
    result.update({
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
    })
    missing = [i['id'] for i in items if i['id'] not in result]
    if missing:
        raise ValueError(f'No range rule for {missing}')
    return result, statements, numbered, labels, lines


S5 = 'Stafford38.Paper.Section5.'
GEO = 'Stafford38.Geometry.'


def ref(file, name, role, **extra):
    return dict(file=file, name=name, repo='formal', role=role, **extra)


def section5_refs():
    main = 'Stafford38/Paper/Section5.lean'
    place = 'Stafford38/Paper/Section5/Place.lean'
    basis = 'Stafford38/Paper/Section5/ResidueBasis.lean'
    cone = 'Stafford38/Paper/Section5/TangentCone.lean'
    rank = 'Stafford38/Paper/Section5/GenericTangentRank.lean'
    core = 'Stafford38/Geometry/DivisorialVisibleFrameCore.lean'
    alternative = ref('Stafford38/Geometry/AlternativeAsymptoticConormal.lean',
                      GEO + 'AlternativeAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure', 'main-proof',
                      note='The printed route of Subsection 5.2.')
    terminal = ref('Stafford38/Geometry/GeneralAsymptoticConormal.lean',
                   GEO + 'GeneralAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure', 'alternative-proof',
                   note='Terminal theorem; proves the same statement by the second, chart-based route.')
    place_frame = ref('Stafford38/Geometry/GeneralDivisorialVisibleFrame.lean',
                      GEO + 'GeneralDivisorialVisibleFrame.generalDivisorialVisibleFrameWithResidueAlgebraicity', 'helper')
    columns = ref('Stafford38/Geometry/PaperActualDivisorTangent.lean',
                  GEO + 'PaperActualDivisorTangent.exists_regularizedOneRowConormalData_of_actual_columns', 'helper')
    # The witness theorems are about the objects of the formal proof; it does not use them.
    witness_11 = ref(main, S5 + 'witness_lemma_5_11', 'supporting result')
    witness_12 = ref(main, S5 + 'witness_lemma_5_12_5_13', 'supporting result')
    return {
        'thm:asymptotic-conormal': [
            ref(main, S5 + 'theorem_5_7_i', 'statement'),
            ref(main, S5 + 'theorem_5_7_ii', 'statement'),
            alternative,
            terminal,
            ref('Stafford38/Geometry/GeneralAsymptoticConormal.lean',
                GEO + 'GeneralAsymptoticConormal.coordinate_axis_mem_projective_conormal_directions', 'alternative-proof'),
            ref('Stafford38/Geometry/ProjectiveConormalDirections.lean',
                GEO + 'ProjectiveConormalDirections.mk_mem_projectiveHomogeneousClosure_of_fibre_zeroLocus', 'helper'),
            ref('Stafford38/Geometry/GeneralCoisotropicExclusion.lean',
                GEO + 'GeneralCoisotropicExclusion.exists_zero_base_coordinate', 'helper'),
        ],
        'lem:W': [
            ref(place, S5 + 'lemma_5_9', 'statement'),
            ref(core, GEO + 'LaneC.stage1_exists_valuationSubring_of_transcendental', 'helper'),
        ],
        'lem:place': [
            ref(place, S5 + 'lemma_5_10', 'statement'),
            ref(core, GEO + 'LaneC.stage3_exists_height_one_prime_valuation', 'helper'),
            ref('Stafford38/Geometry/DivisorialVisibleFrameStageAssembly.lean', GEO + 'LaneC.stage4_of_verified', 'helper'),
            ref(core, GEO + 'LaneC.stage7_kaehler_finite_ofField', 'helper'),
            dict(place_frame, role='supporting result'),
        ],
        'lem:kappa': [
            ref(basis, S5 + 'lemma_5_11', 'statement'),
            witness_11,
            ref('Stafford38/Geometry/KaehlerDVRVisibility.lean',
                GEO + 'KaehlerDVRVisibility.kaehler_span_of_isAlgebraic_adjoin', 'helper'),
        ],
        'lem:tangent': [
            ref(rank, S5 + 'generic_tangent_finrank_eq_component_kaehler_finrank', 'statement'),
            ref(cone, S5 + 'lemma_5_12_b', 'statement'),
            ref(rank, S5 + 'component_kaehler_finrank_eq_trdeg', 'statement'),
            ref(cone, S5 + 'lemma_5_12_a_cone', 'statement'),
            witness_12,
            ref('Stafford38/Geometry/PaperSameWitnessTangentDimension.lean',
                GEO + 'PaperSameWitnessTangentDimension.tangent_finrank_le_residue_add_one_of_witness', 'alternative-support'),
        ],
        'lem:ell': [
            ref(cone, S5 + 'lemma_5_13', 'statement'),
            witness_12,
            ref('Stafford38/Geometry/PaperActualWitnessConormalData.lean',
                GEO + 'PaperActualWitnessConormalData.exists_regularizedOneRowConormalData_of_actual_witness',
                'supporting result'),
        ],
        'proof': dict(main=[ref(main, S5 + 'theorem_5_7_i', 'main-proof'), alternative],
                      paper=[place_frame, columns, witness_11, witness_12],
                      terminal=terminal),
    }


# Same-witness declarations kept on the proof card as the alternative route.
SAME_WITNESS_KEPT = {
    GEO + 'SameWitness.coordinate_axis_mem_smooth_fibre_closure',
    GEO + 'SameWitness.axis_mem_smoothConormalFibreProjection_closure_of_groundPointOutput',
    GEO + 'SameWitness.axis_mem_smoothConormalFibreProjection_closure_of_algHoms',
    GEO + 'SameWitness.exists_axis_lift_of_groundPointChartOutput',
    GEO + 'SameWitness.CommonOpenData',
    GEO + 'SameWitness.nonempty_commonOpenData',
}

NOTES = {
    'formal-verification': (
        'The subsection states that Theorem 1.1 and Corollary 6.3 are proved in Lean from the three standard '
        'axioms, that every intermediate result is proved as well, and that the proof in Sections 3–6 follows '
        'the formal proof step by step, the text saying where the two routes differ. The reader maps the formal '
        'counterparts card by card; a card marked “similar” says where Lean reorganizes a step. In Subsection 5.2 '
        'each printed statement, Theorem 5.7 and Lemmas 5.9–5.13, has its own Lean theorem in '
        'Stafford38.Paper.Section5, and Theorem 5.7 is proved along the printed route. Lemma 4.7 has no exact '
        'Lean declaration mapped here; its content is used inside larger formal results.'),
    'thm:asymptotic-conormal': (
        'Lean theorem_5_7_i and theorem_5_7_ii state (i) and (ii) over any algebraically closed field K of '
        'characteristic zero, the setting of Section 5, for the prime ideal 𝔭 = I(Y) instead of the set Y; '
        'Y ∩ H = ∅ is written as x₁ ≠ 0 on V_K(𝔭). Statement (i) is the membership of (1,0,…,0) in the zero '
        'set of the ideal of polynomials vanishing on N(Y), which is the printed condition. Both are proved by '
        'the printed route (see the proof card). The terminal theorem '
        'GeneralAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure proves the same statement by a '
        'second, chart-based route.'),
    'thm:asymptotic-conormal-proof': (
        'Lean follows the printed proof: the algebraic case, the valuation ring and the discrete valuation ring '
        'at infinity, the differential basis of the residue field, the Laurent generic point y with its tangent '
        'space and cone, the matrix M(t) with a unit minor, and the lift ℓ(t) of the 1-coordinate row with '
        'ℓ(0) = u. theorem_5_7_i applies AlternativeAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure. '
        'The discrete valuation ring is built by '
        'GeneralDivisorialVisibleFrame.generalDivisorialVisibleFrameWithResidueAlgebraicity, and the steps '
        'between the lemmas (λ, τ, M(t) and the lift of ℓ) are in '
        'PaperActualDivisorTangent.exists_regularizedOneRowConormalData_of_actual_columns. One difference: the '
        'formal proof does not call lemma_5_9 and lemma_5_10 themselves. It builds its ring from the same '
        'intermediate results as their proofs, with an additional coefficient field, and witness_lemma_5_11 and '
        'witness_lemma_5_12_5_13 show that this ring and its Laurent column satisfy Lemmas 5.11–5.13, including '
        'the bound dim Θ_y ≤ d′+1. The terminal theorem GeneralAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure '
        'proves the same statement by a second route through SameWitness.coordinate_axis_mem_smooth_fibre_closure; '
        'its key declarations are listed as the alternative proof.'),
    'lem:W': (
        'Lean lemma_5_9: if x̄₁ is transcendental over K, there are a valuation ring W of F with K ⊆ W ≠ F and '
        'x̄₁ ∈ 𝔪_W, and an index j with x̄_j ≠ 0 and x̄ᵢ/x̄_j ∈ W for 0 ≤ i ≤ n, where x̄₀ = 1. The proof is the '
        'printed one: a valuation ring dominating K[x̄₁] localized at x̄₁ (Stacks Tag 00IA), then j maximal '
        'for the preorder x̄_a/x̄_b ∈ W.'),
    'lem:place': (
        'Lean lemma_5_10 takes W and j from Lemma 5.9 and gives a discrete valuation ring V of F containing K '
        'with (a) qᵢ ∈ V, x̄₁ ∈ 𝔪_V and R ⊄ V, (b) κ algebraic over K(res q₀,…,res qₙ) and (c) Ω_{V/K} finitely '
        'generated. Its hypothesis 1 = ḡx̄₁ with ḡ ∈ R is what the paper derives from Y ∩ H = ∅ by the '
        'Nullstellensatz. The proof follows the printed one, through the normalization A of C₀ and a height-one '
        'prime over x̄₁A. The formal proof of Theorem 5.7 builds its ring with '
        'GeneralDivisorialVisibleFrame.generalDivisorialVisibleFrameWithResidueAlgebraicity from the same '
        'intermediate results and an additional coefficient field.'),
    'lem:kappa': (
        'Lean lemma_5_11 takes residues r₀,…,rₙ ∈ κ with r₀ = r₁ = 0, r_j = 1 and κ algebraic over '
        'K(r₀,…,rₙ), and gives distinct indices outside {0,1,j} whose differentials form a basis of Ω_{κ/K}; '
        'their number is dim_κ Ω_{κ/K}. The proof is the printed one: a transcendence basis chosen among these '
        'residues (Lang Thm. VIII.1.1) is a differential basis in characteristic zero (Matsumura Thm. 26.5). '
        'witness_lemma_5_11 shows that the discrete valuation ring of the formal proof of Theorem 5.7 has '
        'res q₀ = res q₁ = 0 and res q_j = 1 and satisfies the lemma.'),
    'lem:tangent': (
        'Lean states the lemma for a column q with q₀ ≠ 0 over a field L ⊇ K, with Θ_y and 𝒞 = ρ⁻¹(Θ_y) as in '
        'the text. (a) generic_tangent_finrank_eq_component_kaehler_finrank gives dim Θ_y = dim_F Ω_{F/K} at the '
        'generic point, component_kaehler_finrank_eq_trdeg gives dim_F Ω_{F/K} = trdeg_K F = m, and '
        'lemma_5_12_a_cone gives dim 𝒞 = dim Θ_y + 1. (b) is lemma_5_12_b. The bound m ≤ d′+1 depends on the '
        'discrete valuation ring; witness_lemma_5_12_5_13 proves it for the ring of the formal proof of '
        'Theorem 5.7 and applies (a) and (b) to its Laurent point. Route: (b) and the cone dimension follow the '
        'printed proof; for dim Θ_y ≥ m Lean uses the derivations of F/K, each of which gives a tangent vector, '
        'instead of the Jacobian rank.'),
    'lem:ell': (
        'Lean lemma_5_13: for q with q₀ ≠ 0, a row vector ℓ annihilating 𝒞 has affine part (ℓ₁,…,ℓₙ) in '
        'span{df_y : f ∈ 𝔭}. The proof is the printed one: ℓ(q) = 0 and ℓ(v) = 0 give Σ ℓᵢρ(v)ᵢ = 0, and '
        'ρ(𝒞) = Θ_y. witness_lemma_5_12_5_13 applies it to the Laurent point of the formal proof of Theorem 5.7.'),
}
ROUTES = {
    'thm:asymptotic-conormal': (
        'Stafford38.Paper.Section5.theorem_5_7_i applies '
        'Stafford38.Geometry.AlternativeAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure, the printed '
        'route; theorem_5_7_ii deduces (ii) from (i) as in the last paragraph of the printed proof.'),
    'thm:asymptotic-conormal-proof': (
        'Main route: Stafford38.Paper.Section5.theorem_5_7_i → '
        'Stafford38.Geometry.AlternativeAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure. Alternative '
        'route: Stafford38.Geometry.GeneralAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure → '
        'Stafford38.Geometry.SameWitness.coordinate_axis_mem_smooth_fibre_closure, which treats the algebraic '
        'case directly and otherwise closes the conormal fibre through a ground point on a common chart '
        '(SameWitness.axis_mem_smoothConormalFibreProjection_closure_of_groundPointOutput).'),
}
RELATIONS = {
    'thm:asymptotic-conormal': ('equivalent', 'similar'),
    'thm:asymptotic-conormal-proof': ('n/a', 'similar'),
    'lem:W': ('exact', 'same'),
    'lem:place': ('exact', 'same'),
    'lem:kappa': ('exact', 'same'),
    'lem:tangent': ('exact', 'similar'),
    'lem:ell': ('exact', 'same'),
}


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
        raise SystemExit('Base revision is already migrated; pass --base-rev of the October 28 map')
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
    # ------------------------------------------------- Section 5.2 cards ----
    refs = section5_refs()
    for identifier in ['thm:asymptotic-conormal', 'lem:W', 'lem:place', 'lem:kappa', 'lem:tangent', 'lem:ell']:
        by_id[identifier]['lean'] = refs[identifier]
    proof = by_id['thm:asymptotic-conormal-proof']
    old_names = [r['name'] for r in proof['lean']]
    route_refs = refs['proof']
    replaced = {r['name'] for r in route_refs['main'] + route_refs['paper']} | {route_refs['terminal']['name']}
    lean = list(route_refs['main'])
    for r in proof['lean']:
        name = r['name']
        if name in replaced:
            continue
        if '.SameWitness.' in name:
            if name in SAME_WITNESS_KEPT:
                lean.append(dict(r, role='definition' if r['role'] == 'definition' else 'alternative-support'))
            continue
        if r['role'] in ('main-proof', 'alternative-support'):
            # Earlier entry points of the printed route are now helpers of theorem_5_7_i.
            r = {k: v for k, v in r.items() if k != 'note'} | {'role': 'helper'}
        lean.append(r)
    lean[2:2] = route_refs['paper']
    lean.append(route_refs['terminal'])
    proof['lean'] = lean
    assert set(SAME_WITNESS_KEPT) <= set(old_names)
    for identifier, note in NOTES.items():
        item = by_id[identifier]
        item['correspondence'] = note
        item['comparison_updated_on'] = UPDATED
        if identifier in ROUTES:
            item['route'] = ROUTES[identifier]
        if identifier in RELATIONS:
            item['statement_relation'], item['route_relation'] = RELATIONS[identifier]
    # ------------------------------------------------- source and texts ----
    source = dict(old_source, commit=commit, origin_commit=commit,
                  sha256=hashlib.sha256(raw.encode()).hexdigest(), label='Paper (frozen version)',
                  note='November 2 frozen version, preserved verbatim.')
    snapshot_files = {}
    snapshot_base = ROOT / 'sources/paper/raw'
    snapshot_base.mkdir(parents=True, exist_ok=True)
    for file in ['human_readable_main.tex', 'references.bib', 'ai_review.tex']:
        content = git(paper, 'show', f'{commit}:{file}')
        (snapshot_base / file).write_text(content)
        snapshot_files[file] = hashlib.sha256(content.encode()).hexdigest()
    source['snapshot'] = dict(base='sources/paper/raw', files=snapshot_files)
    open_findings = sorted(i['id'] for item in items for i in item['issues'] if i['id'].startswith('MS'))
    mapping['version'] = VERSION
    mapping['subtitle'] = 'November 2 manuscript · paper and Lean proof comparison'
    mapping['reader_notice'] = (f'Manuscript updated 2 November 2026. {len(open_findings)} review findings '
                                'are recorded under Comparison notes.')
    mapping['sources']['paper'] = source
    clean = active_tex(raw)
    line_at = lambda pos: clean.count('\n', 0, pos) + 1
    mapping['aicomments'] = [dict(id=m[1], line=line_at(m.start()), verdict='author review pending',
        note='Active annotation in the updated manuscript; no author acceptance is inferred.')
        for m in re.finditer(r'\\AIcomment\{([^{}]+)\}', clean)]
    mapping['provenance'] = mapping['provenance'].replace('the October 28 Overleaf update', 'the November 2 frozen version')
    mapping['comparison_scope'] = mapping['comparison_scope'].replace('October 28', 'November 2')
    mapping['overview'] = (
        'Compare the November 2 frozen manuscript with the pinned Lean results. Every theorem-like statement '
        'has a card. In Subsection 5.2 Theorem 5.7 and Lemmas 5.9–5.13 each have their own Lean theorem, and '
        'Theorem 5.7 is proved in Lean along the printed route; the earlier chart-based proof is kept as an '
        'alternative. Matching conclusions elsewhere do not by themselves certify a printed proof step by step.')
    mapping['candidate']['status'] = 'November 2 frozen manuscript refresh'
    mapping['candidate']['manuscript'] = source
    manifest['version'] = mapping['version']
    manifest['sources'] = mapping['sources']
    manifest['review'].update(claims=len(items), scope=mapping['comparison_scope'],
        statement_relations=dict(collections.Counter(i['statement_relation'] for i in items)),
        proof_routes=dict(collections.Counter(i['route_relation'] for i in items)))
    manifest['status'] = 'manuscript-update-in-progress'
    manifest['checks'] = dict(status='pending', receipt='verification/manuscript-20261102/verification.json',
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
        if i['id'] in NOTES and len(names) != len(set(names)):
            raise ValueError(f'Duplicate Lean reference on {i["id"]}')
    if git(paper, 'status', '--porcelain=v1') != before:
        raise SystemExit('Paper worktree changed during migration')
    history = dict(base_supplementary_revision=base_rev, previous_paper=old_source, current_paper=source,
                   renamed_labels={}, deleted_labels=[], renumbered_statements={},
                   removed_cards=[], added_cards=[], moved_ranges=moved,
                   remapped_cards=sorted(NOTES), active_statements=len(statements), current_cards=len(items),
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
          f'{len(NOTES)} cards remapped; {len(statements)} active statements; '
          f'{len(open_findings)} open findings. Paper unchanged.')


if __name__ == '__main__':
    main()
