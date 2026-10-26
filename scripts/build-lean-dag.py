#!/usr/bin/env python3
"""Render the dependency DAG of the Lean proof to lean-dag.html.

With --formal (a built checkout of the pinned formal commit) the script runs
scripts/LeanDag.lean and scripts/LeanDeclRanges.lean, contracts Lean's own
dependency graph to the key declarations below and stores the result in
verification/lean-dag/graph.json. Without --formal it renders from that file.
Every edge comes from the constants Lean records in the declarations' types
and proofs; nothing is inferred from names. Requires Graphviz (`dot`).
"""
from pathlib import Path
import argparse, importlib.util, json, re, subprocess

root = Path(__file__).resolve().parent.parent
DATA = root / 'verification/lean-dag/graph.json'
spec = importlib.util.spec_from_file_location('paperdag', root / 'scripts/build-proof-dag.py')
paperdag = importlib.util.module_from_spec(spec)
spec.loader.exec_module(paperdag)
esc, label, node, svg, HEAD, LEAN = (paperdag.esc, paperdag.label, paperdag.node,
                                     paperdag.svg, paperdag.HEAD, paperdag.LEAN)

S = 'Stafford38.'
# Key declarations: id -> (Lean declarations, label, paper statement id or None).
# A node stands for all its declarations; 'cited' marks Lean proofs of
# results the paper cites, which the graph treats as inputs.
KEYS = {
    'T': ([S + 'universalStatement'], 'universalStatement: 1 = dR + FdS', 'T1.1'),
    'CYC': ([S + 'TorsionCyclicity.weyl_isCyclic_of_isRightTorsion'],
            'torsion modules are cyclic (induction on generators)', 'C6.3'),
    'ASM': ([S + 'UniversalAssembly.universalStatement_of_canonicalSupportVanishing'],
            'normal form + certificate, transported back by Φ_g⁻¹', 'R3.3'),
    'MON': ([S + 'WeylMonicNormalization.scalar_or_normalized_symplectic_image',
             S + 'WeylMonicNormalization.exists_normalized_symplectic_image'],
            'd scalar, or Φ_g(d) monic in p of degree N', 'P3.2'),
    'SYMP': ([S + 'CharacteristicSymplecticCompletion.exists_symplectic_chart_matrices',
              S + 'CharacteristicSymplecticCompletion.exists_symplectic_mulVec_eq'],
             'symplectic matrix sending e_p to v', 'L3.1'),
    'CERT': ([S + 'CharacteristicCanonicalCertificate.exists_fixedSource_certificate_of_orderCharacteristicSupport_eq_empty'],
             'Char(Q) = ∅ ⇒ 1 ∈ d̃A + x₁^N d̃A', 'T1.1'),
    'VAN': ([S + 'FoundationClosure.canonicalSupportVanishingViaGeneralCoisotropic'],
            'Char(Q) = ∅ over k', 'T1.1'),
    'DESC': ([S + 'PaperQuotientDescent.canonicalSupportDescent_via_quotient'],
             'descent: empty over k̄ ⇒ empty over k', 'L6.2'),
    'EXCL': ([S + 'Geometry.GeneralCoisotropicCanonicalAdapter.algebraicallyClosedCanonicalSupportVanishing_of_generalCoisotropic',
              S + 'Geometry.GeneralCoisotropicCanonicalAdapter.algebraicallyClosedCanonicalSupportVanishing_using'],
             'over k̄: involutive, fibre-conical support avoiding H is empty', 'T5.6'),
    'AXIS': ([S + 'Geometry.GeneralAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure'],
             'P|N(Y) = 0 ⇒ P(1,0,…,0) = 0', 'T5.5'),
    'ARC': ([S + 'Geometry.SameWitness.axis_mem_smoothConormalFibreProjection_closure_of_groundPointOutput'],
            'Laurent arc: conormal covectors tend to dx₁', 'T5.5'),
    'PLACE': ([S + 'Geometry.ActualSameWitnessGroundPointCompletion.exists_actual_same_witness_groundpoint_chart'],
              'divisorial place at infinity with ground-point chart', 'L5.8'),
    'TRDEG': ([S + 'Geometry.SameWitnessTranscendenceDegreeBound.component_trdeg_le_residue_trdeg_add_one_of_witness'],
              'tangent bound: trdeg ≤ residue trdeg + 1', 'L5.10'),
    'BRIDGE': ([S + 'SpecializedNoncharacteristicEquality.strictUnitCoordinatePreimage_of_transposedSupport_disjoint_axis'],
               'support avoiding H ⇒ x₁ is a strict unit on gr Q', None),
    'AVOID': ([S + 'Characteristic.CanonicalKoszulContradiction.canonical_support_avoidance',
               S + 'Characteristic.CanonicalSupportAvoidanceFromCokernel.canonical_support_avoidance_of_coordinate_cokernel_subsingleton'],
              'Char(Q) ∩ π⁻¹(H) = ∅', 'P6.1'),
    'UZERO': ([S + 'Characteristic.CanonicalKoszulContradiction.coordinate_cokernel_subsingleton'],
              'U = M/x₁M = 0', 'C4.11'),
    'STRICT': ([S + 'Characteristic.NoncharacteristicMinimalPrime.canonical_minimalPrime_mem_of_normalCoordinate_false'],
               'x₁ lies in no minimal prime of √Ann M', 'L4.10'),
    'PAGE': ([S + 'Characteristic.CanonicalPageEulerInequality.canonicalPage_length_target_le_source'],
             'ℓ(U_𝔮) ≤ ℓ(V_𝔮)', 'L4.9'),
    'FIN': ([S + 'Characteristic.CanonicalOldTangentialFiniteness.canonical_finite_old_coordinate_kernel_cokernel'],
            'U, V finite over T', 'L4.8'),
    'SURJ': ([S + 'WeylQuotientTransport.presentedCanonicalRightQuotient_rightMul_coordinate_surjective'],
             'Q = Qx₁', 'P4.3'),
    'EULER': ([S + 'WeylEulerRemainder.presentedPositiveEulerResidue'], '1 + Ux₁ ∈ I', 'L4.2'),
    'CHARP': ([S + 'CharacteristicInitialIdeal.canonical_orderPrincipalComponent_mem_initialIdeal'],
              'P lies in the initial ideal of I', 'P3.6'),
    'MONICP': ([S + 'Characteristic.NormalSymbolPolynomial.canonicalNormalPolynomial_monic'],
               'P monic in ξ₁', 'L3.5'),
    'GABBER': ([S + 'Characteristic.GabberGlobalAssembly.associatedGraded_radical_isInvolutive',
                S + 'Characteristic.GabberGlobalAssembly.minimalPrime_isInvolutive'],
               'Gabber: √Ann gr M and its minimal primes are involutive', 'cited'),
}
GABBER_SOURCE = 'Gab81 · SK14 · HTT 2.3.1; proved in Lean'

# Cited external inputs: id -> (label, source, module prefixes). Theorems
# from these modules count as uses; general algebra (ideals, polynomials,
# finiteness, …) is not drawn.
LEAVES = {
    'ore': ('Ore extensions: Weyl normal form', 'AlgebraicAnalysis Ore.*', ['AlgebraicAnalysis.Ore.']),
    'pages': ('filtered two-term pages', 'AlgebraicAnalysis Module.FilteredTwoTerm*',
              ['AlgebraicAnalysis.Module.FilteredTwoTerm', 'AlgebraicAnalysis.Module.TwoTermPageLength',
               'AlgebraicAnalysis.Module.UniformBoundaryVanishing']),
    'aasupp': ('minimal support, localized lengths, Koszul positivity', 'AlgebraicAnalysis Module.*',
               ['AlgebraicAnalysis.Module.']),
    'nss': ('Nullstellensatz', 'paper Thm 2.8; Mathlib RingTheory.Nullstellensatz, Jacobson',
            ['Mathlib.RingTheory.Nullstellensatz', 'Mathlib.RingTheory.Jacobson']),
    'length': ('length, Artinian and Noetherian modules', 'paper Def 4.6; Mathlib RingTheory.Length, SimpleModule, Artinian',
               ['Mathlib.RingTheory.Length', 'Mathlib.RingTheory.FiniteLength', 'Mathlib.RingTheory.SimpleModule',
                'Mathlib.RingTheory.Artinian', 'Mathlib.RingTheory.HopkinsLevitzki', 'Mathlib.RingTheory.Noetherian']),
    'support': ('support, localization, local rings, Nakayama', 'paper §4, Stacks 00L2, 00L3, 00DV; Mathlib',
                ['Mathlib.RingTheory.Support', 'Mathlib.RingTheory.Localization', 'Mathlib.RingTheory.Spectrum',
                 'Mathlib.RingTheory.Ideal.MinimalPrime', 'Mathlib.RingTheory.LocalRing', 'Mathlib.RingTheory.Nakayama',
                 'Mathlib.RingTheory.QuotSMulTop']),
    'flat': ('flat base change, algebraic closure', 'Stacks 05DT; Mathlib RingTheory.Flat, IsAlgClosed',
             ['Mathlib.RingTheory.Flat', 'Mathlib.RingTheory.TensorProduct', 'Mathlib.FieldTheory.IsAlgClosed']),
    'val': ('valuations, DVRs, integral closure, Krull dimension', 'paper Lemmas 5.7, 5.8 inputs; Mathlib',
            ['Mathlib.RingTheory.Valuation', 'Mathlib.RingTheory.DiscreteValuationRing',
             'Mathlib.RingTheory.DedekindDomain', 'Mathlib.RingTheory.IntegralClosure',
             'Mathlib.RingTheory.NoetherNormalization', 'Mathlib.RingTheory.KrullDimension',
             'Mathlib.RingTheory.Ideal.Height', 'Mathlib.RingTheory.Ideal.KrullsHeightTheorem',
             'Mathlib.RingTheory.Ideal.GoingUp']),
    'series': ('power and Laurent series, adic completion', 'Stacks 0C0S; Mathlib',
               ['Mathlib.RingTheory.PowerSeries', 'Mathlib.RingTheory.MvPowerSeries', 'Mathlib.RingTheory.LaurentSeries',
                'Mathlib.RingTheory.HahnSeries', 'Mathlib.RingTheory.AdicCompletion']),
    'kahler': ('Kähler differentials, étale and smooth maps, transcendence', 'Hartshorne II.8; Mathlib',
               ['Mathlib.RingTheory.Kaehler', 'Mathlib.RingTheory.Etale', 'Mathlib.RingTheory.Smooth',
                'Mathlib.RingTheory.Unramified', 'Mathlib.RingTheory.Derivation', 'Mathlib.RingTheory.AlgebraicIndependent',
                'Mathlib.RingTheory.Algebraic', 'Mathlib.RingTheory.RegularLocalRing', 'Mathlib.RingTheory.EssentialFiniteness',
                'Mathlib.FieldTheory.Separable', 'Mathlib.FieldTheory.Perfect', 'Mathlib.FieldTheory.PurelyInseparable',
                'Mathlib.FieldTheory.IntermediateField', 'Mathlib.FieldTheory.Minpoly']),
    'coprime': ('coprime polynomials (Bézout)', 'Mathlib RingTheory.Coprime', ['Mathlib.RingTheory.Coprime']),
    'symp': ('symplectic group', 'Mathlib LinearAlgebra.SymplecticGroup', ['Mathlib.LinearAlgebra.SymplecticGroup']),
}
ORDER = ['T', 'CYC', 'ASM', 'MON', 'SYMP', 'CERT', 'VAN', 'DESC', 'BRIDGE', 'EXCL', 'GABBER', 'AXIS',
         'ARC', 'PLACE', 'TRDEG', 'AVOID', 'UZERO', 'STRICT', 'PAGE', 'FIN', 'SURJ', 'EULER', 'CHARP', 'MONICP']
assert sorted(ORDER) == sorted(KEYS)
HELPERS = 6  # direct helper lemmas drawn per theorem graph


def leaf_of(module):
    """The first leaf whose prefix matches; earlier leaves take precedence."""
    for lid, (_, _, prefixes) in LEAVES.items():
        if any(module.startswith(p) for p in prefixes):
            return lid
    return None


def lean(formal, script, *args):
    subprocess.run(['lake', 'env', 'lean', '--run', str(root / 'scripts' / script), *map(str, args)],
                   cwd=formal, check=True)


def extract(formal):
    work = DATA.parent
    work.mkdir(parents=True, exist_ok=True)
    raw_path = work / '.raw.json'
    lean(formal, 'LeanDag.lean', raw_path)
    raw = json.loads(raw_path.read_text())
    raw_path.unlink()
    g, ext = raw['constants'], raw['externals']
    owner = {name: nid for nid, (names, _, _) in KEYS.items() for name in names}
    missing = [n for n in owner if n not in g]
    if missing:
        raise SystemExit('unknown key declarations: ' + ', '.join(missing))

    def result(name):
        """A theorem that is not an instance (by attribute or Lean's `inst` naming) or projection."""
        return (name in ext and ext[name][1] == 'theorem' and not ext[name][2]
                and not name.rpartition('.')[2].startswith('inst'))

    def visible(name):
        last = name.rpartition('.')[2]
        return (g[name]['kind'] == 'theorem' and '._' not in name and not name.startswith('_private')
                and not re.fullmatch(r'eq_\d+|eq_def|match_\d+|proof_\d+', last))

    memo = {}
    def reach(start, stop):
        """Keys and leaves reached from `start` through constants outside `stop`."""
        if start in memo:
            return memo[start]
        keys, leaves, todo, seen = set(), set(), [start], {start}
        while todo:
            c = todo.pop()
            for e in g[c]['external']:
                if result(e) and (lid := leaf_of(ext[e][0])):
                    leaves.add(lid)
            for d in g[c]['uses']:
                if d in owner and d not in stop:
                    keys.add(owner[d])
                elif d in g and d not in seen and d not in owner:
                    seen.add(d)
                    todo.append(d)
        memo[start] = keys, leaves
        return memo[start]

    nodes = {}
    for nid, (names, _, _) in KEYS.items():
        keys, leaves, direct = set(), set(), {}
        for name in names:
            k, l = reach(name, set(names))
            keys |= k
            leaves |= l
            for d in g[name]['uses']:
                if d in g and d not in owner and visible(d):
                    hk, hl = reach(d, set(names))
                    direct[d] = dict(keys=sorted(hk - {nid}), leaves=sorted(hl))
        nodes[nid] = dict(keys=sorted(keys - {nid}), leaves=sorted(leaves), helpers=direct)

    names = sorted({n for names, _, _ in KEYS.values() for n in names} |
                   {h for v in nodes.values() for h in v['helpers']})
    lst, mods = work / '.names.txt', work / '.modules.txt'
    lst.write_text('\n'.join(names) + '\n')
    mods.write_text('Stafford38\nSolution\nFixedSourceSolution\n')
    lean(formal, 'LeanDeclRanges.lean', mods, lst, lst.with_suffix('.json'))
    ranges = json.loads(lst.with_suffix('.json').read_text())
    for path in (lst, mods, lst.with_suffix('.json')):
        path.unlink()
    head = subprocess.check_output(['git', '-C', str(formal), 'rev-parse', 'HEAD'], text=True).strip()
    DATA.write_text(json.dumps(dict(
        schema=1, formal_commit=head,
        source='Constants used by types and proofs (scripts/LeanDag.lean); lines from findDeclarationRanges?.',
        nodes=nodes, ranges={n: ranges[n] for n in names if n in ranges}), indent=1, ensure_ascii=False) + '\n')


def source_href(ranges, name):
    module, line = ranges[name]
    return f'./sources/formal/{module.replace(".", "/")}.lean.html#L{line}'


def reduce_leaves(nodes):
    """Draw a leaf only into the first nodes that use it: drop X -> K when a
    key below K (one K depends on) already uses X."""
    below = {}
    def closure(nid):
        if nid not in below:
            below[nid] = set()
            for k in nodes[nid]['keys']:
                below[nid] |= {k} | closure(k)
        return below[nid]
    return {nid: [l for l in v['leaves'] if not any(l in nodes[b]['leaves'] for b in closure(nid))]
            for nid, v in nodes.items()}


def reduce_keys(nodes):
    """Transitive reduction of the key edges (Lean edges skipping a level)."""
    out = {}
    for nid, v in nodes.items():
        direct = set(v['keys'])
        def deps(k, seen):
            for j in nodes[k]['keys']:
                if j not in seen:
                    seen.add(j); deps(j, seen)
            return seen
        implied = set().union(*[deps(k, set()) for k in direct]) if direct else set()
        out[nid] = sorted(direct - implied)
    return out


def kind(nid):
    return 'cited' if KEYS[nid][2] == 'cited' else ('goal' if nid in ('T', 'CYC') else 'stmt')


def name_lines(name, width):
    """Break a Lean name after underscores and dots so it fits `width`."""
    lines, line = [], ''
    for part in [p for p in name.replace('_', '_\0').replace('.', '.\0').split('\0') if p]:
        if line and len(line) + len(part) > width:
            lines.append(line); line = part
        else:
            line += part
    return lines + [line]


def lean_label(nid, width, ref_line=True):
    """Paper counterpart as title, the claim, then the Lean name in small type."""
    names, text, ref = KEYS[nid]
    head = ('cited: Thm 2.7 (Gabber)' if ref == 'cited' else
            ('≈ ' + paperdag.ST[ref][0] if ref in paperdag.ST else 'formal only'))
    small = names[0].split('.')[-1] + (f' (+{len(names) - 1})' if len(names) > 1 else '')
    parts = [f'<B>{esc(head)}</B>'] + [esc(l) for l in paperdag.wrap(text, width)]
    if ref == 'cited':
        parts.append(f'<FONT POINT-SIZE="7.5">{esc(GABBER_SOURCE)}</FONT>')
    parts += [f'<FONT POINT-SIZE="7.5">{esc(l)}</FONT>' for l in name_lines(small, width + 8)]
    return '<' + '<BR/>'.join(parts) + '>'


def overall_dot(data):
    nodes, ranges = data['nodes'], data['ranges']
    keys, leaves = reduce_keys(nodes), reduce_leaves(nodes)
    out = ['digraph G {\n', HEAD.replace('nodesep=0.18', 'nodesep=0.12')]
    for name, gloss in LEAN:
        out.append(node('A:' + name, label(name, gloss), 'lean'))
    out.append('  { rank=min; ' + ' '.join(f'"A:{n}"' for n, _ in LEAN) + ' }\n')
    out.append(node('logic', label('Lean 4 kernel', 'universalStatement depends on these three only', width=26), 'logic'))
    for name, _ in LEAN:
        out.append(f'  "A:{name}" -> "logic";\n')
    used = sorted({l for ls in leaves.values() for l in ls}, key=list(LEAVES).index)
    for lid in used:
        text, src, _ = LEAVES[lid]
        out.append(node('X:' + lid, label(None, text, src, width=20), 'cited', href=f'#leaf-{lid}'))
    for nid in ORDER:
        names, text, ref = KEYS[nid]
        extra = dict(peripheries=2) if nid in ('T', 'CYC') else {}
        out.append(node(nid, lean_label(nid, 24), kind(nid),
                        href='#' + nid, tooltip=esc(names[0]), **extra))
        if not nodes[nid]['keys']:
            out.append(f'  "logic" -> "{nid}" [class="lean" style=dotted];\n')
    out.append('  { rank=max; "CYC" }\n')
    for nid in ORDER:
        for k in keys[nid]:
            out.append(f'  "{k}" -> "{nid}";\n')
        for lid in leaves[nid]:
            out.append(f'  "X:{lid}" -> "{nid}" [class="ext" style=dashed];\n')
    out.append('}\n')
    return ''.join(out)


def proof_dot(data, nid):
    nodes, ranges = data['nodes'], data['ranges']
    v = nodes[nid]
    names, text, ref = KEYS[nid]
    out = ['digraph G {\n', HEAD]
    inputs = [('K:' + k, k) for k in v['keys']] + [('X:' + l, l) for l in v['leaves']]
    for key, ident in inputs:
        if key.startswith('K:'):
            kn, kt, kr = KEYS[ident]
            out.append(node(key, lean_label(ident, 30), 'cited' if kr == 'cited' else 'dep',
                            href='#' + ident))
        else:
            lt, ls, _ = LEAVES[ident]
            out.append(node(key, label(None, lt, ls, width=30), 'cited', href=f'#leaf-{ident}'))
    if inputs:
        out.append('  { rank=min; ' + ' '.join(f'"{k}"' for k, _ in inputs) + ' }\n')
    helpers = sorted(v['helpers'].items(), key=lambda kv: (-len(kv[1]['keys']) - len(kv[1]['leaves']), kv[0]))
    shown = [h for h in helpers if h[1]['keys'] or h[1]['leaves']][:HELPERS]
    covered = set()
    for i, (h, hv) in enumerate(shown):
        hid = f'h{i}'
        lines = '<BR/>'.join(esc(l) for l in name_lines(h.split('.')[-1], 34))
        out.append(node(hid, f'<{lines}>', 'step',
                        href=source_href(ranges, h) if h in ranges else '', tooltip=esc(h)))
        for k in hv['keys']:
            out.append(f'  "K:{k}" -> "{hid}";\n'); covered.add('K:' + k)
        for l in hv['leaves']:
            out.append(f'  "X:{l}" -> "{hid}" [class="ext" style=dashed];\n'); covered.add('X:' + l)
        out.append(f'  "{hid}" -> "goal";\n')
    rest = len(v['helpers']) - len(shown)
    if rest > 0:
        out.append(node('more', label(None, f'+ {rest} further lemmas used directly', width=40), 'std'))
        out.append('  "more" -> "goal" [style=dotted];\n')
    for key, _ in inputs:
        if key not in covered:
            style = ' [class="ext" style=dashed]' if key.startswith('X:') else ''
            out.append(f'  "{key}" -> "goal"{style};\n')
    out.append(node('goal', lean_label(nid, 44), 'goal', peripheries=2,
                    href=source_href(ranges, names[0])))
    out.append('  { rank=max; "goal" }\n}\n')
    return ''.join(out)


def page(data):
    nodes, ranges = data['nodes'], data['ranges']
    kinds = [('lean', 'Lean base axiom'), ('cited', 'cited input (library or cited paper result)'),
             ('dep', 'key Lean theorem used'), ('stmt', 'key Lean theorem'), ('step', 'helper lemma'),
             ('goal', 'proved theorem (exits)')]
    legend = ''.join(f'<li style="--f:var(--{paperdag.FILL[c]});--k:var(--{paperdag.FILL[c]}k)">{t}</li>'
                     for c, t in kinds)
    cards = []
    for nid in ORDER:
        names, text, ref = KEYS[nid]
        dot = proof_dot(data, nid)
        wide = ' wide' if paperdag.width(dot) > 640 else ''
        paper = (f'<a href="proof-dag.html#{paperdag.anchor(ref)}">{esc(paperdag.ST[ref][0])} graph</a> · '
                 if ref in paperdag.ST else '')
        decls = ' · '.join(f'<a href="{source_href(ranges, n)}"><code>{esc(n.removeprefix("Stafford38."))}</code></a>'
                           for n in names if n in ranges)
        cards.append(f'<article class="card{wide}" id="{nid}"><header><h3>{esc(text)}</h3>'
                     f'<span>{paper}<a href="#overall">overall</a></span></header><p class="mute">{decls}</p>'
                     f'<div class="fig">{svg(dot)}</div></article>')
    rows = []
    for lid, (text, src, prefixes) in LEAVES.items():
        users = [KEYS[n][1] for n in ORDER if lid in nodes[n]['leaves']]
        rows.append(f'<tr id="leaf-{lid}"><td>{esc(text)}</td><td>{esc(src)}</td>'
                    f'<td><code>{esc(", ".join(p.rstrip(".") for p in prefixes))}</code></td>'
                    f'<td>{len(users)}</td></tr>')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stafford 3.8 Lean graph</title>
<meta name="description" content="Dependency DAG of the Lean proof of Stafford's Conjecture 3.8, computed from Lean's environment.">
<style>{paperdag.STYLE}</style>
</head><body>
<main>
<p class="mute"><a href="index.html">← Proof comparison</a> · <a href="proof-dag.html">Paper proof graph</a></p>
<h1>Lean proof graph</h1>
<p>Building blocks of the Lean proof (formal commit {data['formal_commit'][:7]}) and how they combine.
Every edge is computed from the constants Lean records in each declaration's type and proof
(<code>scripts/LeanDag.lean</code>), contracted to the {len(KEYS)} key declarations below. Arrows run from
premise to consequence. Library results and Lean proofs of results the paper cites appear as cited
inputs. Click a node to open its graph or source.</p>
<ul class="legend">{legend}</ul>
<h2 id="overall">From the axioms to universalStatement</h2>
<p>Key edges are transitively reduced. A cited input is drawn only into the first nodes that use it:
an edge is omitted when a node it depends on already uses that input. General algebra (ideals,
polynomials, finiteness) is not drawn.</p>
<div class="fig bleed">{svg(overall_dot(data), shrink=False)}</div>
<h2 id="theorems">One graph per key theorem</h2>
<p>Inputs enter at the top: the key theorems and cited inputs the proof reaches without passing
another key theorem. The middle row shows the named lemmas the Lean proof uses directly, at most
{HELPERS}, chosen by how many inputs they carry. The theorem exits at the bottom.</p>
<div class="grid">{"".join(cards)}</div>
<h2 id="leaves">Cited inputs</h2>
<p>A theorem from one of these modules, used by a key declaration, counts as a use of the input.</p>
<div class="tbl"><table><thead><tr><th>Input</th><th>Source</th><th>Lean modules</th><th>Key theorems</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p class="mute">Generated by <code>scripts/build-lean-dag.py</code> from
<code>verification/lean-dag/graph.json</code>. The graph is a reading aid for the checked proof.</p>
</main>
</body></html>
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--formal', type=Path, help='built checkout of the pinned formal commit')
    args = parser.parse_args()
    if args.formal:
        extract(args.formal.resolve())
    data = json.loads(DATA.read_text())
    (root / 'lean-dag.html').write_text(page(data))
    paperdag.refresh_checksums()
    print(f'Wrote lean-dag.html: {len(KEYS)} key theorems, '
          f'{len({l for v in data["nodes"].values() for l in v["leaves"]})} cited inputs.')
