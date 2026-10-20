#!/usr/bin/env python3
"""Render the proof-dependency DAGs of the printed paper to proof-dag.html.

Each printed proof becomes one graph: hypotheses and inputs enter at the
top, the proved statement exits at the bottom. The overall graph is derived
from the same data, so the per-proof and overall views cannot disagree.
Results the paper cites, and standard facts it uses without a citation, are
drawn as axioms together with their source. Requires Graphviz (`dot`).
Afterwards the file checksums in manifest.json and SHA256SUMS are refreshed.
"""
from pathlib import Path
import hashlib, html, json, re, subprocess

root = Path(__file__).resolve().parent.parent
TEX = 'sources/paper/human_readable_main.tex.html'

# The three axioms checked for the Lean headline declarations
# (verification/canonical-definitions/logs/axioms.log).
LEAN = [('propext', 'propositional extensionality'),
        ('Classical.choice', 'global choice'),
        ('Quot.sound', 'quotient soundness')]

# External inputs, taken as axioms: (label, source, kind).
# kind 'cited': the paper gives the source; 'std': used without a citation;
# 'warn': an input the printed text does not supply.
EXT = {
    'gabber': ('Gabber: √Ann gr M is involutive (stated as Thm 3.7)',
               'Gabber 1981; Singh–Kumar 2014; Hotta–Takeuchi–Tanisaki Thm 2.3.1, App. D', 'cited'),
    'grpoly': ('gr A_n = k[x,ξ], commutative; symbols multiply',
               'Schnell, D-modules notes, Prop. 2.10', 'cited'),
    'loc': ('Localization: fractions, exactness',
            'Stacks Tag 00CM (Def. 6.1)', 'cited'),
    'length': ('Length well defined, additive on short exact sequences',
               'Coutinho; Cohn; Stacks Tags 02LY, 00J3, 00IV (Def. 6.3)', 'cited'),
    'vasc': ('Vasconcelos: surjective endomorphism of a finite module is injective',
             'Matsumura, Commutative Ring Theory, Thm 2.4', 'cited'),
    '00L2': ('Support is closed under specialization',
             'Stacks Lemma 10.40.5, Tag 00L2', 'cited'),
    'nak': ("Nakayama's lemma",
            'Nakayama 1951; Stacks Tag 00DV', 'cited'),
    '00L3': ('Supp(M/xM) = Supp M ∩ V(x) for finite M',
             'Stacks Tag 00L3', 'cited'),
    '0C0S': ('Coefficient field: completion of V is κ[[t]]',
             'Stacks Tag 0C0S', 'cited'),
    'hartII8': ('dim_F Ω_{F/K} = trdeg_K F (char 0); conormal sequence',
                'Hartshorne, Algebraic Geometry II.8', 'cited'),
    'hartI14': ('V(prime) is closed and irreducible',
                'Hartshorne, Algebraic Geometry Cor. I.1.4', 'cited'),
    '05DT': ('Annihilator of a finite module commutes with flat base change',
             'Stacks Tag 05DT', 'cited'),
    'staff37': ('Stafford: f.g. torsion modules need 2 generators',
                'Stafford 1978, Thm 3.7, p. 438', 'cited'),
    'nss': ("Hilbert's Nullstellensatz (stated as Thm 9.2)",
            'stated without citation', 'std'),
    'alg': ('Field facts: char 0 ⇒ k infinite, ℚ ⊂ k, m! ≠ 0; Bézout in ℚ[E]; ranks and minors',
            'standard; no citation', 'std'),
    'weyl': ('Weyl algebra basics: presentation, PBW basis, Weyl relations, commutators lower the order',
             'standard; no citation (Convention 3.1)', 'std'),
    'comm': ('Noetherian algebra: ACC, finite submodules, minimal primes, primes avoiding a multiplicative set',
             'standard; no citation', 'std'),
    'val': ('Chevalley extension; finite normalization; Krull PIT; normal ⇒ DVR at height one',
            'named in the proof; no citation', 'std'),
    'kahler': ('Kähler differentials: finite for f.g. algebras, localize, vanish on separable algebraic extensions',
               'standard; no citation', 'std'),
    'smdense': ('Smooth locus Y_sm is dense in Y',
                'standard; no citation', 'std'),
    'ore': ('A_n is a right Ore domain', 'standard; no citation', 'std'),
    'fl': ('Finite module, support = {closed point} ⇒ finite length',
           'used, not argued in the printed proof', 'warn'),
    'conormal': ('Conormal space N*_y Y0 = span{df_y : f ∈ 𝔮}',
                 'cites “Definition ??”: def:conormal lies in a comment', 'warn'),
}

# Compact labels for the overall graph: (name, short source).
TAG = {
    'gabber': ('Gabber involutivity', 'Gab81 · SK14 · HTT 2.3.1'),
    'grpoly': ('gr A_n = k[x,ξ]', 'Schnell Prop 2.10'),
    'loc': ('localization exact', 'Stacks 00CM'),
    'length': ('length additive', 'Coutinho · Cohn · Stacks 02LY'),
    'vasc': ('Vasconcelos', 'Matsumura Thm 2.4'),
    '00L2': ('support up-closed', 'Stacks 00L2'),
    'nak': ('Nakayama', 'Nak51 · Stacks 00DV'),
    '00L3': ('Supp(M/xM)', 'Stacks 00L3'),
    '0C0S': ('coefficient field', 'Stacks 0C0S'),
    'hartII8': ('dim Ω = trdeg', 'Hartshorne II.8'),
    'hartI14': ('V(prime) irreducible', 'Hartshorne I.1.4'),
    '05DT': ('Ann flat base change', 'Stacks 05DT'),
    'staff37': ('Stafford 2 generators', 'Sta78 Thm 3.7'),
    'nss': ('Nullstellensatz', 'Thm 9.2, uncited'),
    'alg': ('field facts', 'uncited'),
    'weyl': ('Weyl/PBW basics', 'uncited'),
    'comm': ('Noetherian algebra', 'uncited'),
    'val': ('valuations, normalization, Krull', 'named, uncited'),
    'kahler': ('Kähler differentials', 'uncited'),
    'smdense': ('Y_sm dense', 'uncited'),
    'ore': ('Ore domain', 'uncited'),
    'fl': ('finite length at minimal 𝔮', 'not argued'),
    'conormal': ('conormal space', 'Definition ??'),
}
assert TAG.keys() == EXT.keys()

# Printed statements: number, short claim, tex line of statement, section.
ST = {
    'T1.1': ('Theorem 1.1', '1 = dR + FdS, F = ℓ^{deg_B d}', 95, 'Intro'),
    'L4.1': ('Lemma 4.1', 'symplectic completion: g ω-preserving, g(e) = v', 374, '§4 Monic normal form'),
    'P4.2': ('Proposition 4.2', 'd̃ = c⁻¹Φ_g(d) monic in p of degree N', 423, '§4 Monic normal form'),
    'R4.3': ('Remark 4.3', 'identity for d̃ transports back to d', 484, '§4 Monic normal form'),
    'L4.5': ('Lemma 4.5', 'σ_ord(d̃) = P(ξ), monic in ξ₁, P(1,0,…,0) = 1', 507, '§4 Monic normal form'),
    'S5': ('§5 setup', 'x₁ normal in A_{≥0}; Euler degree ≥ 1 ⇒ ∈ A_{≥0}x₁', 551, '§5 Euler surjectivity'),
    'L5.1': ('Lemma 5.1', 'x₁^m p^m, p^m x₁^m are products of (E ± i)', 567, '§5 Euler surjectivity'),
    'L5.2': ('Lemma 5.2', '1 + Ux₁ ∈ I for some U ∈ A_{≥0}', 594, '§5 Euler surjectivity'),
    'P5.3': ('Proposition 5.3', 'Q = Qx₁', 621, '§5 Euler surjectivity'),
    'L6.4': ('Lemma 6.4', '𝔭 ∈ Supp N ⇔ ∃y, Ann(y) ⊆ 𝔭', 678, '§6 Vanishing cokernel'),
    'L6.5': ('Lemma 6.5', 'U, V finite over T; Supp V ⊆ Supp U', 703, '§6 Vanishing cokernel'),
    'L6.6': ('Lemma 6.6', 'ℓ(U_𝔮) ≤ ℓ(V_𝔮)', 752, '§6 Vanishing cokernel'),
    'L6.7': ('Lemma 6.7', 'ℓ(U_𝔮) > ℓ(V_𝔮)', 857, '§6 Vanishing cokernel'),
    'L6.8': ('Lemma 6.8', 'U = M/x₁M = 0', 935, '§6 Vanishing cokernel'),
    'C7.1': ('Corollary 7.1', 'P ∈ Ann gr Q', 951, '§7 Characteristic variety'),
    'P7.2': ('Proposition 7.2', 'Char(Q) ∩ π⁻¹(H) = ∅', 966, '§7 Characteristic variety'),
    'L8.2': ('Lemma 8.2', 'divisorial place V with x̄₁ ∈ 𝔪_V, R ⊄ V', 1427, '§8 Conormal direction at infinity'),
    'L8.3': ('Lemma 8.3', 'residue field κ, derivations D_k', 1462, '§8 Conormal direction at infinity'),
    'L8.4': ('Lemma 8.4', 'tangent space: dim C ≤ d + 2, δq ∈ C', 1488, '§8 Conormal direction at infinity'),
    'T8.5': ('Theorem 8.5', 'P|N(Y) = 0 ⇒ P(1,0,…,0) = 0; [dx₁] ∈ Dir(Y)', 1522, '§8 Conormal direction at infinity'),
    'T9.3': ('Theorem 9.3', 'involutive exclusion: W ∩ π⁻¹(H) ≠ ∅', 1891, '§9 Involutive obstruction'),
    'L10.1': ('Lemma 10.1', 'base change: gr Q_K = gr Q ⊗ K; Q = 0 ⇔ Q_K = 0', 1955, '§10 Proof of Theorem 1.1'),
    'C10.2': ('Corollary 10.2', 'f.g. torsion right A_n-modules are cyclic', 2043, '§10 Proof of Theorem 1.1'),
}

# One graph per printed proof. Node keys: 'X:…' external, 'D:…' earlier
# statement, otherwise local ('h…' hypothesis, 's…' step, 'goal').
# Local nodes are (key, kind, text); edges are (source, target).
PROOFS = [
 dict(id='L4.1', line=381, nodes=[
    ('h1', 'hyp', '(𝕍, ω) symplectic, dim 2n'), ('h2', 'hyp', 'v ≠ 0, e ≠ 0'),
    ('s1', 'step', 'ω nondegenerate ⇒ ∃w, ω(v,w) = 1'),
    ('s2', 'step', 'ω|U nondegenerate, U = span(v,w)'),
    ('s3', 'step', '𝕍 = U ⊕ U^⊥, ω|U^⊥ nondegenerate'),
    ('s4', 'step', 'induction on n: symplectic basis e₁ = v'),
    ('s5', 'step', 'complete e likewise; map basis to basis'),
    ('goal', 'goal', 'v starts a symplectic basis;\n∃ ω-preserving g with g(e) = v')],
  edges=[('h1', 's1'), ('h2', 's1'), ('s1', 's2'), ('s2', 's3'), ('X:alg', 's3'),
         ('s3', 's4'), ('s4', 's5'), ('s5', 'goal')]),
 dict(id='P4.2', line=433, nodes=[
    ('h1', 'hyp', 'd ≠ 0, N = deg_B d ≥ 1'), ('h2', 'hyp', 'char k = 0'),
    ('s1', 'step', 'Bernstein symbol s ≠ 0, homogeneous of degree N;\npick v with s(v) ≠ 0, so v ≠ 0'),
    ('s2', 'step', 'h ω-preserving with h(e_p) = v'),
    ('s3', 'step', 'g := hᵀ is ω-preserving (J⁻¹ = −J)'),
    ('s4', 'step', 'Φ_g(d) ≡ s(Mu) mod B_{N−1};\ndeg_B = N, c := s_g(e_p) = s(v) ≠ 0'),
    ('s5', 'step', 'd̃ = c⁻¹Φ_g(d) = Σ p^j a_j, deg_B a_j ≤ N − j'),
    ('s6', 'step', 'evaluate the symbol at e_p ⇒ a_N = 1'),
    ('goal', 'goal', 'd̃ = p^N + Σ_{j<N} p^j a_j,\na_j ∈ C, deg_B a_j ≤ N − j')],
  edges=[('h1', 's1'), ('h2', 's1'), ('X:alg', 's1'), ('s1', 's2'), ('D:L4.1', 's2'),
         ('s2', 's3'), ('s3', 's4'), ('X:weyl', 's4'), ('X:grpoly', 's4'),
         ('s4', 's5'), ('X:weyl', 's5'), ('s5', 's6'), ('s6', 'goal')]),
 dict(id='R4.3', line=484, nodes=[
    ('h1', 'hyp', '1 = d̃R + x₁^N d̃S'),
    ('s1', 'step', 'apply the automorphism Φ_g⁻¹;\nc ∈ k^× is central'),
    ('goal', 'goal', '1 = d(c⁻¹Φ_g⁻¹R) + F d(c⁻¹Φ_g⁻¹S),\nF = Φ_g⁻¹(x₁)^N')],
  edges=[('h1', 's1'), ('D:P4.2', 's1'), ('s1', 'goal')]),
 dict(id='L4.5', line=519, nodes=[
    ('h1', 'hyp', 'd̃ as in (4.1), N = deg_B d̃'),
    ('s1', 'step', 'order-N PBW monomials have |α| = 0:\npure ∂^β with scalar coefficient'),
    ('s2', 'step', 'order N; σ_ord(d̃) = P(ξ), homogeneous of degree N'),
    ('s3', 'step', 'only p^N reaches ξ₁^N ⇒ c_N = 1'),
    ('goal', 'goal', 'σ_ord(d̃) = P(ξ), monic in ξ₁,\nP(1,0,…,0) = 1')],
  edges=[('h1', 's1'), ('D:P4.2', 's1'), ('X:weyl', 's1'), ('s1', 's2'), ('s1', 's3'),
         ('s2', 'goal'), ('s3', 'goal')]),
 dict(id='L5.1', line=575, nodes=[
    ('h1', 'hyp', 'E = x₁p, m ≥ 0'),
    ('s1', 'step', 'x₁E = (E − 1)x₁, Ep = p(E − 1)'),
    ('s2', 'step', 'induction on m (m = 0 trivial)'),
    ('goal', 'goal', 'x₁^m p^m = ∏_{i<m}(E − i),\np^m x₁^m = ∏_{i=1}^{m}(E + i)')],
  edges=[('h1', 's1'), ('X:weyl', 's1'), ('s1', 's2'), ('s2', 'goal')]),
 dict(id='L5.2', line=600, nodes=[
    ('h1', 'hyp', 'I = d̃A_n + x₁^N d̃A_n'),
    ('s1', 'step', 'R₊(E) = p^N x₁^N, R₋(E) = x₁^N p^N'),
    ('s2', 'step', 'roots {−1,…,−N} ∩ {0,…,N−1} = ∅ ⇒ gcd = 1'),
    ('s3', 'step', 'uR₊ + vR₋ = 1, u, v ∈ ℚ[E]'),
    ('s4', 'step', '(d̃x₁^N)u + (x₁^N d̃)v = 1 + w ∈ I'),
    ('s5', 'step', 'each term of w has Euler degree > 0\n⇒ w = Ux₁, U ∈ A_{≥0}'),
    ('goal', 'goal', '∃U ∈ A_{≥0} with 1 + Ux₁ ∈ I')],
  edges=[('D:L5.1', 's1'), ('s1', 's2'), ('s2', 's3'), ('X:alg', 's3'), ('h1', 's4'),
         ('s3', 's4'), ('D:P4.2', 's4'), ('s4', 's5'), ('D:S5', 's5'), ('s5', 'goal')]),
 dict(id='P5.3', line=624, nodes=[
    ('h1', 'hyp', 'q = class of 1 in Q'),
    ('s1', 'step', 'q = −qUx₁ ∈ (qA_{≥0})x₁'),
    ('s2', 'step', 'normality x₁r = r′x₁ ⇒ qA_{≥0} = (qA_{≥0})x₁'),
    ('s3', 'step', 'qA_{≥0} stable under p (m′x₁p = m′E) and C'),
    ('s4', 'step', 'C and p generate A_n ⇒ qA_{≥0} = Q'),
    ('goal', 'goal', 'right multiplication by x₁ on Q\nis surjective: Q = Qx₁')],
  edges=[('h1', 's1'), ('D:L5.2', 's1'), ('s1', 's2'), ('D:S5', 's2'), ('s2', 's3'),
         ('s3', 's4'), ('X:weyl', 's4'), ('s2', 'goal'), ('s4', 'goal')]),
 dict(id='L6.4', line=684, nodes=[
    ('h1', 'hyp', 'R commutative, N an R-module, 𝔭 prime'),
    ('s1', 'step', 'y/1 = 0 in N_𝔭 ⇔ Ann(y) ⊄ 𝔭'),
    ('s2', 'step', '(⇐) y/1 ≠ 0 ⇒ N_𝔭 ≠ 0'),
    ('s3', 'step', '(⇒) y/s ≠ 0 ⇒ y/1 ≠ 0 (s a unit)'),
    ('goal', 'goal', '𝔭 ∈ Supp N ⇔ ∃y ∈ N, Ann(y) ⊆ 𝔭')],
  edges=[('h1', 's1'), ('X:loc', 's1'), ('s1', 's2'), ('s1', 's3'), ('s2', 'goal'), ('s3', 'goal')]),
 dict(id='L6.5', line=711, nodes=[
    ('h1', 'hyp', 'M = gr Q, f = ·x₁, V = ker f, U = coker f,\nT = k[x₂…x_n, ξ₂…ξ_n]'),
    ('s1', 'step', 'M finite over T[x₁] via T[x₁,ξ₁]/(P),\nbasis 1, ξ₁, …, ξ₁^{N−1}'),
    ('s2', 'step', 'U, V finite over T[x₁], killed by x₁\n⇒ finite over T'),
    ('s3', 'step', '𝔭 ∈ Supp_T V ⇒ ∃𝔮 ∈ Supp ker f, 𝔮 ∩ (T∖𝔭) = ∅'),
    ('s4', 'step', 'Supp ker f ⊆ Supp coker f'),
    ('s5', 'step', 'back to T: 𝔭 ∈ Supp_T U'),
    ('s6', 'step', 'finite length at a minimal 𝔮'),
    ('goal', 'goal', 'U, V finite over T; Supp_T V ⊆ Supp_T U;\nU_𝔮, V_𝔮 of finite length')],
  edges=[('h1', 's1'), ('D:C7.1', 's1'), ('D:L4.5', 's1'), ('s1', 's2'), ('X:comm', 's2'),
         ('s2', 's3'), ('D:L6.4', 's3'), ('X:comm', 's3'), ('s3', 's4'), ('X:vasc', 's4'),
         ('X:loc', 's4'), ('s4', 's5'), ('D:L6.4', 's5'), ('s2', 's6'), ('s5', 's6'),
         ('X:fl', 's6'), ('s2', 'goal'), ('s5', 'goal'), ('s6', 'goal')]),
 dict(id='L6.6', line=760, nodes=[
    ('h1', 'hyp', '𝔮 minimal in Supp_T U'),
    ('s1', 'step', 'filtered complex Q →(·x₁) Q, G^p = F_{−p}Q;\npages A_r, B_r, d_r; A₁ = V, B₁ = U'),
    ('s2', 'step', 'T acts on the pages; d_r is T-linear'),
    ('s3', 'step', 'localize at 𝔮: all pages of finite length'),
    ('s4', 'step', 'Q = Qx₁ ⇒ each class of B₁\ndies on a later page'),
    ('s5', 'step', 'ACC ⇒ ∃R, (B_R)_𝔮 = 0'),
    ('s6', 'step', 'telescoping lengths:\nℓ(U_𝔮) + ℓ((A_R)_𝔮) = ℓ(V_𝔮)'),
    ('goal', 'goal', 'ℓ(U_𝔮) ≤ ℓ(V_𝔮)')],
  edges=[('s1', 's2'), ('X:weyl', 's2'), ('h1', 's3'), ('s2', 's3'), ('D:L6.5', 's3'),
         ('X:loc', 's3'), ('s1', 's4'), ('D:P5.3', 's4'), ('s3', 's5'), ('s4', 's5'),
         ('X:comm', 's5'), ('s5', 's6'), ('X:length', 's6'), ('s6', 'goal')]),
 dict(id='L6.7', line=864, nodes=[
    ('h1', 'hyp', '𝔮 minimal in Supp_T U'),
    ('s1', 'step', '√Ann M involutive'),
    ('s2', 'step', 'minimal primes 𝔭 of √Ann M involutive\n(localize at 𝔭)'),
    ('s3', 'step', 'x₁ ∉ 𝔭: N-fold {x₁, ·} of P gives N! ∈ 𝔭'),
    ('s4', 'step', 'K = ker f_𝔮^m stable, of finite length'),
    ('s5', 'step', 'ℓ(K/x₁K) = ℓ(V_𝔮)'),
    ('s6', 'step', 'ℓ(U_𝔮) = ℓ(V_𝔮) + ℓ(E/x₁E), E = M_𝔮/K'),
    ('s7', 'step', 'K_𝔭 = 0 ⇒ E_𝔭 ≠ 0 ⇒ E_𝔓 ≠ 0'),
    ('s8', 'step', 'x₁ ∈ 𝔓 ⇒ (E/x₁E)_𝔓 ≠ 0'),
    ('goal', 'goal', 'ℓ(U_𝔮) > ℓ(V_𝔮)')],
  edges=[('X:gabber', 's1'), ('s1', 's2'), ('X:loc', 's2'), ('s2', 's3'), ('D:C7.1', 's3'),
         ('D:L4.5', 's3'), ('X:alg', 's3'), ('h1', 's4'), ('D:L6.5', 's4'), ('X:comm', 's4'),
         ('s4', 's5'), ('X:length', 's5'), ('s4', 's6'), ('s5', 's6'), ('X:length', 's6'),
         ('s3', 's7'), ('s6', 's7'), ('X:00L2', 's7'), ('X:comm', 's7'), ('s7', 's8'),
         ('X:nak', 's8'), ('s6', 'goal'), ('s8', 'goal')]),
 dict(id='L6.8', line=939, nodes=[
    ('s1', 'step', 'if U ≠ 0: a minimal prime 𝔮 ∈ Supp_T U'),
    ('s2', 'step', 'ℓ(U_𝔮) ≤ ℓ(V_𝔮) < ℓ(U_𝔮): contradiction'),
    ('goal', 'goal', 'U = M/x₁M = 0')],
  edges=[('D:L6.5', 's1'), ('X:comm', 's1'), ('s1', 's2'), ('D:L6.6', 's2'),
         ('D:L6.7', 's2'), ('s2', 'goal')]),
 dict(id='C7.1', line=959, nodes=[
    ('h1', 'hyp', 'Q = A_n/I cyclic, q = [1];\nQ_m = qF_m'),
    ('s1', 'step', 'Q_• is good (Q cyclic)'),
    ('s2', 'step', 'qd̃ = 0, qd̃ ∈ Q_N ⇒ q̄·P = 0 in Q_N/Q_{N−1}'),
    ('s3', 'step', 'gr Q is generated by q̄'),
    ('goal', 'goal', 'P ∈ Ann_{k[x,ξ]} gr Q')],
  edges=[('h1', 's1'), ('h1', 's2'), ('D:L4.5', 's2'), ('X:grpoly', 's2'), ('s1', 's3'),
         ('s2', 'goal'), ('s3', 'goal')]),
 dict(id='P7.2', line=969, nodes=[
    ('h1', 'hyp', 'M = gr Q finite over k[x,ξ]'),
    ('s1', 'step', 'Supp(M/x₁M) = Supp M ∩ V(x₁) = ∅'),
    ('s2', 'step', 'Supp M = Char Q (Def. 3.4), V(x₁) = π⁻¹(H)'),
    ('goal', 'goal', 'Char(Q) ∩ π⁻¹(H) = ∅')],
  edges=[('h1', 's1'), ('X:00L3', 's1'), ('D:L6.8', 's1'), ('s1', 's2'), ('s2', 'goal')]),
 dict(id='L8.2', line=1437, nodes=[
    ('h1', 'hyp', 'Y = V(𝔭) ⊆ 𝔸^n_K, Y ∩ H = ∅;\nR = K[x]/𝔭, F = Frac R'),
    ('h2', 'hyp', 'x̄₁ transcendental over K'),
    ('s1', 'step', 'valuation ring W ⊇ K[x̄₁], x̄₁ ∈ 𝔪_W'),
    ('s2', 'step', 'chart j: q_a = Z_a/Z_j ∈ W;\nC₀ = K[q, x̄₁] ⊆ W'),
    ('s3', 'step', 'A = integral closure of C₀: f.g., normal, A ⊆ W'),
    ('s4', 'step', 'height-one 𝔭_D ∋ x̄₁; V = A_{𝔭_D} is a DVR'),
    ('s5', 'step', 'x̄₁⁻¹ ∈ R ⇒ R ⊄ V'),
    ('goal', 'goal', '(a) q_j = 1, q_i ∈ A, A integral over C₀;\n(b) V DVR, x̄₁ ∈ 𝔪_V, R ⊄ V')],
  edges=[('h2', 's1'), ('X:val', 's1'), ('s1', 's2'), ('s2', 's3'), ('X:val', 's3'),
         ('s3', 's4'), ('X:val', 's4'), ('s4', 's5'), ('h1', 's5'), ('X:nss', 's5'),
         ('s4', 'goal'), ('s5', 'goal')]),
 dict(id='L8.3', line=1472, nodes=[
    ('h1', 'hyp', 'κ = V/𝔪_V, q̄_i residues of q_i'),
    ('s1', 'step', '(a) κ algebraic over L = K(q̄₀, …, q̄_n)'),
    ('s2', 'step', '(b) transcendence basis among q̄_i, i ∉ {0,1,j};\ndq̄ basis of Ω_κ, dual D_k'),
    ('s3', 'step', '(c) Ω_{V/K} = V ⊗ Ω_{A/K} is finite'),
    ('goal', 'goal', 'κ algebraic over L; d = dim Ω_{κ/K} finite\nwith derivations D_k; Ω_{V/K} finite')],
  edges=[('h1', 's1'), ('D:L8.2', 's1'), ('s1', 's2'), ('X:kahler', 's2'), ('X:alg', 's2'),
         ('D:L8.2', 's3'), ('X:kahler', 's3'), ('s1', 'goal'), ('s2', 'goal'), ('s3', 'goal')]),
 dict(id='L8.4', line=1499, nodes=[
    ('h1', 'hyp', 'T_y = ∩ ker df_y, π: κ((t))^{n+1} → κ((t))^n,\nC = π⁻¹(T_y)'),
    ('s1', 'step', 'dim T_y = m = trdeg F; m ≤ d + 1 (Nakayama)'),
    ('s2', 'step', '(b) δq ∈ C for every K-derivation δ'),
    ('s3', 'step', '(c) ℓ ⊥ C ⇒ (ℓ₁,…,ℓ_n) ∈ span{df_y}'),
    ('goal', 'goal', '(a) dim C ≤ d + 2; (b) δq ∈ C;\n(c) annihilators of C are conormal')],
  edges=[('h1', 's1'), ('X:hartII8', 's1'), ('X:kahler', 's1'), ('X:nak', 's1'), ('D:L8.3', 's1'),
         ('h1', 's2'), ('h1', 's3'), ('s1', 'goal'), ('s2', 'goal'), ('s3', 'goal')]),
 dict(id='T8.5', line=1534, nodes=[
    ('h1', 'hyp', 'K = K̄, char 0; Y ⊆ 𝔸^n nonempty,\nclosed, irreducible, Y ∩ H = ∅'),
    ('s0', 'step', 'x̄₁ algebraic: x₁ = c ≠ 0 on Y ⇒ dx₁ ∈ N(Y)'),
    ('s1', 'step', 'x̄₁ transcendental: DVR V, F ↪ κ((t)),\ngeneric point y'),
    ('s2', 'step', 'a = ord q₀ > 0, b − a = ord x̄₁ > 0'),
    ('s3', 'step', 'M = [q | Z | τ]: rank d + 2, M(0) ⊆ {Z₁ = 0}'),
    ('s4', 'step', 'columns of M span C'),
    ('s5', 'step', 'lift u = Z₁^∨ to ℓ(t), ℓM = 0, ℓ(0) = u'),
    ('s6', 'step', 'ℓ̃ ∈ span{dg_y : g ∈ 𝔭}, ℓ̃(0) = (1,0,…,0)'),
    ('s7', 'step', 'P|N(Y) = 0 ⇒ P(ℓ̃) = 0 ⇒ P(1,0,…,0) = 0'),
    ('goal', 'goal', '(i) P|N(Y) = 0 ⇒ P(1,0,…,0) = 0\n(ii) [dx₁] ∈ Dir(Y)')],
  edges=[('h1', 's0'), ('X:alg', 's0'), ('h1', 's1'), ('D:L8.2', 's1'), ('X:0C0S', 's1'),
         ('s1', 's2'), ('s2', 's3'), ('D:L8.3', 's3'), ('X:alg', 's3'), ('s3', 's4'),
         ('D:L8.4', 's4'), ('s4', 's5'), ('X:alg', 's5'), ('s5', 's6'), ('D:L8.4', 's6'),
         ('s6', 's7'), ('X:smdense', 's7'), ('X:alg', 's7'), ('s0', 'goal'), ('s7', 'goal')]),
 dict(id='T9.3', line=1905, nodes=[
    ('h1', 'hyp', 'K = K̄, char 0; W ⊆ T*X nonempty, closed,\nfibre-conical, involutive'),
    ('h2', 'hyp', 'P(1,0,…,0) ≠ 0, P|W = 0'),
    ('h3', 'hyp', 'assume W ∩ π⁻¹(H) = ∅'),
    ('s1', 'step', 'J = I(W) is ξ-homogeneous; B = J ∩ K[x]'),
    ('s2', 'step', 'Y = V(B) = π(W), Y × {0} ⊆ W, Y ∩ H = ∅'),
    ('s3', 'step', '{f, ·} preserves J for f ∈ B ⇒\n{y} × span{df_y : f ∈ B} ⊆ W'),
    ('s4', 'step', 'minimal prime 𝔮 of B: Y₀ = V(𝔮) ≠ ∅,\nirreducible, Y₀ ∩ H = ∅'),
    ('s5', 'step', 's𝔮 ⊆ B ⇒ {y} × span{dh_y : h ∈ 𝔮} ⊆ W'),
    ('s6', 'step', 'N(Y₀) ⊆ W ⇒ P|N(Y₀) = 0'),
    ('s7', 'step', 'P(1,0,…,0) = 0: contradiction'),
    ('goal', 'goal', 'W ∩ π⁻¹(H) ≠ ∅')],
  edges=[('h1', 's1'), ('X:alg', 's1'), ('s1', 's2'), ('h3', 's2'), ('X:nss', 's2'),
         ('h1', 's3'), ('s2', 's3'), ('X:alg', 's3'), ('s2', 's4'), ('X:comm', 's4'),
         ('X:nss', 's4'), ('X:hartI14', 's4'), ('s3', 's5'), ('s4', 's5'), ('s5', 's6'),
         ('X:conormal', 's6'), ('h2', 's6'), ('s6', 's7'), ('s4', 's7'), ('D:T8.5', 's7'),
         ('h2', 's7'), ('s7', 'goal')]),
 dict(id='L10.1', line=1966, nodes=[
    ('h1', 'hyp', 'K/k field extension;\nI_K, Q_K = A_n(K)/I_K'),
    ('s1', 'step', 'PBW: F_iA_n(K) = F_iA_n(k) ⊗ K,\nI_K = I ⊗ K, Q_{K,i} = Q_i ⊗ K'),
    ('s2', 'step', 'K flat over k ⇒ gr Q_K = gr Q ⊗ K'),
    ('s3', 'step', 'Ann gr Q_K = (Ann gr Q) K[x,ξ]'),
    ('s4', 'step', 'K free nonzero ⇒ (Q ⊗ K = 0 ⇒ Q = 0)'),
    ('goal', 'goal', 'gr Q_K ≅ gr Q ⊗ K; Ann extends; Q = 0 ⇔ Q_K = 0;\nChar(Q_K) = preimage of Char(Q)')],
  edges=[('h1', 's1'), ('X:weyl', 's1'), ('s1', 's2'), ('X:alg', 's2'), ('s2', 's3'),
         ('X:05DT', 's3'), ('h1', 's4'), ('s3', 'goal'), ('s4', 'goal')]),
 dict(id='T1.1', line=1977, nodes=[
    ('h1', 'hyp', 'char k = 0, n ≥ 1, 0 ≠ d ∈ A_n(k),\nN = deg_B d'),
    ('s0', 'step', 'N = 0: d ∈ k^×; F = 1, R = d⁻¹, S = 0'),
    ('s1', 'step', 'N ≥ 1: suffices Q = A_n/(d̃A_n + x₁^N d̃A_n) = 0'),
    ('s2', 'step', 'K = k̄, W = Char(Q_K), I(W) = √Ann gr Q_K'),
    ('s3', 'step', 'W closed and fibre-conical'),
    ('s4', 'step', 'I(W) involutive'),
    ('s5', 'step', 'P|W = 0 and P(1,0,…,0) = 1'),
    ('s6', 'step', 'W ∩ π⁻¹(H) = ∅'),
    ('s7', 'step', 'W = ∅ (contrapositive of Thm 9.3)'),
    ('s8', 'step', '1 ∈ Ann gr Q_K ⇒ gr Q_K = 0\n⇒ Q_K = 0 ⇒ Q = 0'),
    ('s9', 'step', '1 = d̃R + x₁^N d̃S'),
    ('goal', 'goal', '1 = dR + FdS with F = Φ_g⁻¹(x₁)^N')],
  edges=[('h1', 's0'), ('h1', 's1'), ('D:P4.2', 's1'), ('s1', 's2'), ('X:nss', 's2'),
         ('s2', 's3'), ('s2', 's4'), ('X:gabber', 's4'), ('X:grpoly', 's4'),
         ('s2', 's5'), ('D:C7.1', 's5'), ('D:L10.1', 's5'), ('D:L4.5', 's5'),
         ('s2', 's6'), ('D:P7.2', 's6'), ('D:L10.1', 's6'),
         ('s3', 's7'), ('s4', 's7'), ('s5', 's7'), ('s6', 's7'), ('D:T9.3', 's7'),
         ('s7', 's8'), ('X:nss', 's8'), ('D:L10.1', 's8'), ('s8', 's9'),
         ('s9', 'goal'), ('D:R4.3', 'goal'), ('s0', 'goal')]),
 dict(id='C10.2', line=2047, nodes=[
    ('h1', 'hyp', 'T a f.g. torsion right A_n-module'),
    ('s1', 'step', 'T = t₁A_n + t₂A_n ≅ (A_n ⊕ A_n)/M'),
    ('s2', 'step', 'common annihilator d = d₁r₁ = d₂r₂ ≠ 0'),
    ('s3', 'step', '1 = dR + FdS ⇒ (a, 1 − Fa) ∈ M, a = dS'),
    ('s4', 'step', 'A_n ⊕ A_n = (a, 1 − Fa)A_n + (1, −F)A_n'),
    ('goal', 'goal', 'T is cyclic, generated by the image of (1, −F)')],
  edges=[('h1', 's1'), ('X:staff37', 's1'), ('s1', 's2'), ('X:ore', 's2'), ('s2', 's3'),
         ('D:T1.1', 's3'), ('s3', 's4'), ('s4', 'goal')]),
]

# Unnumbered §5 setup claim, recorded as a statement with its own inputs.
SETUP = {'S5': dict(line=551, nodes=[
    ('h1', 'hyp', 'Euler grading by [E, ·], E = x₁p'),
    ('s1', 'step', 'Ex₁ = x₁(E + 1), x₁E = (E − 1)x₁ (5.0)'),
    ('goal', 'goal', 'x₁ normal in A_{≥0};\nEuler degree ≥ 1 ⇒ ∈ A_{≥0}x₁')],
  edges=[('h1', 's1'), ('X:weyl', 's1'), ('s1', 'goal')])}

NOTES = {
    'L4.5': 'The hypothesis is the output of Proposition 4.2.',
    'S5': 'Argued in the text before Lemma 5.1; the explicit justification of the second claim is commented out in the source.',
    'L6.5': 'The finite-length claim for a minimal prime is stated but not argued in the printed proof; it is shown as an unsupplied input.',
    'L6.7': 'The proof writes Ann_C M and names the radical I in one sentence and J in the next; both mean √Ann_{k[x,ξ]} M.',
    'P7.2': 'The manuscript prints two identical proofs; one graph covers both.',
    'L8.2': 'Step (5) uses x̄₁⁻¹ ∈ R. This follows from Y ∩ H = ∅ by the Nullstellensatz, which the proof leaves implicit.',
    'T9.3': 'The conormal space is taken from “Definition ??”: the label def:conormal sits inside a comment environment, so the printed reference is unresolved.',
    'T1.1': 'Theorem 9.3 is applied in contrapositive form. The n = 0 case is noted only in the formal-verification remark.',
    'C10.2': 'Stafford’s two-generator theorem and the Ore property are used as inputs.',
}

ORDER = ['L4.1', 'P4.2', 'R4.3', 'L4.5', 'S5', 'L5.1', 'L5.2', 'P5.3', 'L6.4', 'L6.5',
         'L6.6', 'L6.7', 'L6.8', 'C7.1', 'P7.2', 'L8.2', 'L8.3', 'L8.4', 'T8.5', 'T9.3',
         'L10.1', 'T1.1', 'C10.2']
proofs = {p['id']: p for p in PROOFS} | SETUP
assert sorted(proofs) == sorted(ORDER) == sorted(ST)


def anchor(sid):
    return 'p-' + sid.replace('.', '-')


def esc(text):
    return html.escape(text, quote=False)


def wrap(text, width):
    lines = []
    for para in text.split('\n'):
        line = ''
        for word in para.split(' '):
            if line and len(line) + 1 + len(word) > width:
                lines.append(line)
                line = word
            else:
                line = f'{line} {word}' if line else word
        lines.append(line)
    return lines


def label(title, body, small=None, width=34):
    parts = [f'<B>{esc(title)}</B>'] if title else []
    parts += [esc(line) for line in wrap(body, width)]
    if small:
        parts += [f'<FONT POINT-SIZE="7.5">{esc(line)}</FONT>' for line in wrap(small, width + 6)]
    return '<' + '<BR/>'.join(parts) + '>'


def node(key, lab, cls, **attrs):
    extra = ''.join(f' {k}="{v}"' for k, v in attrs.items())
    return f'  "{key}" [label={lab} class="{cls}"{extra}];\n'


HEAD = ('  graph [fontname="Helvetica" fontsize=10 nodesep=0.18 ranksep=0.28 pad=0.05 bgcolor="transparent"];\n'
        '  node [shape=box style="rounded" fontname="Helvetica" fontsize=9 margin="0.08,0.03" height=0.3];\n'
        '  edge [arrowsize=0.55 penwidth=0.9];\n')


def proof_dot(sid):
    p = proofs[sid]
    out = ['digraph G {\n', HEAD]
    kinds = {k: kind for k, kind, _ in p['nodes']}
    for key, kind, text in p['nodes']:
        if kind == 'goal':
            out.append(node(key, label(ST[sid][0], text, width=48), 'goal', peripheries=2))
        else:
            out.append(node(key, label(None, text, width=48), kind))
    used = {x for e in p['edges'] for x in e if ':' in x}
    for ref in sorted(used):
        tag, name = ref.split(':')
        if tag == 'X':
            text, src, kind = EXT[name]
            out.append(node(ref, label(None, text, src), kind, href=f'#ext-{name}'))
        else:
            num, claim, _, _ = ST[name]
            out.append(node(ref, label(num, claim), 'dep', href='#' + anchor(name)))
    ins = [k for k, kind in kinds.items() if kind == 'hyp'] + sorted(used)
    out.append('  { rank=min; ' + ' '.join(f'"{k}"' for k in ins if k in kinds) + ' }\n')
    out.append('  { rank=max; "goal" }\n')
    for a, b in p['edges']:
        style = ' class="ext" style=dashed' if a.startswith('X:') else ''
        out.append(f'  "{a}" -> "{b}" [{style.strip()}];\n')
    out.append('}\n')
    return ''.join(out)


def uses():
    edges = {}
    for sid in ORDER:
        for a, _ in proofs[sid]['edges']:
            if ':' in a:
                edges.setdefault(sid, set()).add(a)
    return edges


def overall_dot():
    deps = uses()
    out = ['digraph G {\n', HEAD.replace('nodesep=0.18', 'nodesep=0.12'),
           '  compound=true; newrank=true;\n']
    for name, gloss in LEAN:
        out.append(node('A:' + name, label(name, gloss), 'lean'))
    out.append('  { rank=min; ' + ' '.join(f'"A:{n}"' for n, _ in LEAN) + ' }\n')
    out.append(node('logic', label('classical logic of every step',
                                   'the Lean proof of Thm 1.1 uses only these three', width=26),
                    'logic'))
    for name, _ in LEAN:
        out.append(f'  "A:{name}" -> "logic";\n')
    used_ext = sorted({r[2:] for refs in deps.values() for r in refs if r.startswith('X:')},
                      key=list(EXT).index)
    for name in used_ext:
        tag, src = TAG[name]
        out.append(node('X:' + name, label(None, tag, src, width=18), EXT[name][2],
                        href=f'#ext-{name}', tooltip=esc(EXT[name][0])))
    for sid in ORDER:
        num, claim, _, _ = ST[sid]
        kind, extra = ('goal', dict(peripheries=2)) if sid == 'T1.1' else ('stmt', {})
        out.append(node(sid, label(num, claim, width=22), kind, href='#' + anchor(sid), **extra))
        if not any(r.startswith('D:') for r in deps.get(sid, ())):
            out.append(f'  "logic" -> "{sid}" [class="lean" style=dotted];\n')
    out.append('  { rank=max; "C10.2" }\n')
    for sid in ORDER:
        for ref in sorted(deps.get(sid, ())):
            a = ref[2:]
            if ref.startswith('X:'):
                out.append(f'  "X:{a}" -> "{sid}" [class="ext" style=dashed];\n')
            else:
                out.append(f'  "{a}" -> "{sid}";\n')
    out.append('}\n')
    return ''.join(out)


def acyclic():
    deps = {sid: {r[2:] for r in refs if r.startswith('D:')} for sid, refs in uses().items()}
    seen, done = set(), set()
    def visit(s, path):
        assert s not in path, 'cycle: ' + ' -> '.join(path + [s])
        if s in done:
            return
        for t in deps.get(s, ()):
            visit(t, path + [s])
        done.add(s)
    for s in ORDER:
        visit(s, [])


def width(dot):
    out = subprocess.run(['dot', '-Tsvg'], input=dot, capture_output=True, text=True, check=True).stdout
    return float(re.search(r'<svg width="([\d.]+)pt"', out)[1]) * 4 / 3


def svg(dot, shrink=True):
    out = subprocess.run(['dot', '-Tsvg'], input=dot, capture_output=True, text=True, check=True).stdout
    out = out[out.index('<svg'):]
    cap = 'max-width:100%' if shrink else 'max-width:none'
    out = re.sub(r'<svg width="([\d.]+)pt" height="([\d.]+)pt"',
                 lambda m: f'<svg role="img" style="width:{float(m[1]) * 4 / 3:.0f}px;{cap}"', out)
    out = re.sub(r'<title>[^<]*</title>\n?', '', out)
    out = re.sub(r'<!--.*?-->\n?', '', out, flags=re.S)
    return out.replace('xlink:href="#', 'href="#')


STYLE = '''
:root{--bg:#fbfaf7;--fg:#1d1d1f;--mute:#5f6368;--line:#d9d6cf;--card:#fff;
--hyp:#e6f2ea;--hypk:#2f7a4a;--step:#ffffff;--stepk:#8a8f98;--goal:#ece6f7;--goalk:#5b3fa0;
--dep:#e5eef9;--depk:#2d5f9e;--cited:#fbf0d9;--citedk:#a06a00;--std:#f1f1ef;--stdk:#7b7b74;
--warn:#fbe4e1;--warnk:#b3261e;--lean:#e8e2d4;--leank:#4a3f2a;--edge:#6d6f73;--cl:#f3f1ec}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;
--bg:#17181a;--fg:#e8e6e1;--mute:#a3a7ad;--line:#3a3c40;--card:#1f2023;
--hyp:#1e3326;--hypk:#7cc797;--step:#232427;--stepk:#7d828a;--goal:#2c2540;--goalk:#b9a2f0;
--dep:#1d2a3b;--depk:#86aee6;--cited:#3a2f17;--citedk:#e2b65a;--std:#28292b;--stdk:#a19f97;
--warn:#3d1f1d;--warnk:#f0938b;--lean:#332d22;--leank:#d9c9a3;--edge:#9a9da2;--cl:#1c1d20}}
:root[data-theme="dark"]{color-scheme:dark;
--bg:#17181a;--fg:#e8e6e1;--mute:#a3a7ad;--line:#3a3c40;--card:#1f2023;
--hyp:#1e3326;--hypk:#7cc797;--step:#232427;--stepk:#7d828a;--goal:#2c2540;--goalk:#b9a2f0;
--dep:#1d2a3b;--depk:#86aee6;--cited:#3a2f17;--citedk:#e2b65a;--std:#28292b;--stdk:#a19f97;
--warn:#3d1f1d;--warnk:#f0938b;--lean:#332d22;--leank:#d9c9a3;--edge:#9a9da2;--cl:#1c1d20}
body{background:var(--bg);color:var(--fg);font:15px/1.5 Helvetica,Arial,sans-serif;margin:0}
main{max-width:1100px;margin:0 auto;padding-inline:16px;padding-block:24px 64px}
h1{font-size:1.6rem;margin:0 0 .3rem}h2{font-size:1.2rem;margin:2.2rem 0 .4rem}
h3{font-size:1rem;margin:0}a{color:var(--depk)}p{max-width:72ch}.mute{color:var(--mute)}
.legend{display:flex;flex-wrap:wrap;gap:.4rem .9rem;font-size:.85rem;margin:.8rem 0;padding:0;list-style:none}
.legend li::before{content:"";display:inline-block;width:.9em;height:.9em;margin-right:.35em;
vertical-align:-.1em;border:1.5px solid var(--k);background:var(--f);border-radius:3px}
.fig{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px;margin:.6rem 0}
.fig svg{display:block;height:auto;margin:0 auto}.card.wide{flex-basis:100%}
.grid{display:flex;flex-wrap:wrap;gap:14px}.grid .card{flex:1 1 auto;min-width:min(100%,300px);max-width:100%;box-sizing:border-box}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px 12px}
.card .fig{border:0;padding:4px 0;margin:.3rem 0}.card p{font-size:.85rem;margin:.3rem 0}
.card header{display:flex;justify-content:space-between;gap:.5rem;align-items:baseline}
.card header span{font-size:.8rem;white-space:nowrap}
.bleed{margin-inline:calc(50% - 50vw + 16px)}
table{border-collapse:collapse;font-size:.85rem;width:100%}
td,th{border-bottom:1px solid var(--line);padding:.35rem .5rem;text-align:left;vertical-align:top}
.tbl{overflow-x:auto}
svg text{fill:var(--fg)!important;font-family:Helvetica,Arial,sans-serif}
svg .edge path{stroke:var(--edge)}svg .edge polygon{fill:var(--edge);stroke:var(--edge)}
svg .cluster polygon{fill:var(--cl);stroke:var(--line)}
svg .node path,svg .node polygon,svg .node ellipse{stroke-width:1.2}
'''
KINDS = [('lean', 'Lean base axiom'), ('cited', 'cited result (axiom, with source)'),
         ('std', 'standard fact, uncited (axiom)'), ('warn', 'input the text does not supply'),
         ('hyp', 'hypothesis (enters)'), ('dep', 'earlier result of the paper'),
         ('step', 'proof step'), ('stmt', 'paper statement'), ('goal', 'proved statement (exits)')]
FILL = dict(lean='lean', cited='cited', std='std', warn='warn', hyp='hyp', dep='dep',
            step='step', stmt='dep', goal='goal', logic='lean')
for cls, var in FILL.items():
    STYLE += (f'svg .node.{cls} path,svg .node.{cls} polygon{{fill:var(--{var});stroke:var(--{var}k)}}\n')
STYLE += 'svg .node.goal path,svg .node.goal polygon{stroke-width:1.6}\n'


def page():
    acyclic()
    legend = ''.join(f'<li style="--f:var(--{FILL[c]});--k:var(--{FILL[c]}k)">{t}</li>' for c, t in KINDS)
    cards = []
    for sid in ORDER:
        num, claim, line, _ = ST[sid]
        p = proofs[sid]
        note = f'<p class="mute">{esc(NOTES[sid])}</p>' if sid in NOTES else ''
        cards.append(
            f'<article class="card{" wide" if width(proof_dot(sid)) > 640 else ""}" id="{anchor(sid)}"><header><h3>{esc(num)}</h3>'
            f'<span><a href="{TEX}#L{line}">statement</a> · <a href="{TEX}#L{p["line"]}">proof</a></span></header>'
            f'<p>{esc(claim)}</p><div class="fig">{svg(proof_dot(sid))}</div>{note}</article>')
    rows = []
    deps = uses()
    for name, (text, src, kind) in EXT.items():
        users = [ST[s][0] for s in ORDER if 'X:' + name in deps.get(s, ())]
        rows.append(f'<tr id="ext-{name}"><td>{esc(text)}</td><td>{esc(src)}</td>'
                    f'<td>{esc(", ".join(users))}</td></tr>')
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Stafford 3.8 proof graph</title>
<meta name="description" content="Dependency DAGs of every printed proof in the Stafford Conjecture 3.8 paper.">
<style>{STYLE}</style>
</head><body>
<main>
<p class="mute"><a href="index.html">← Proof comparison</a></p>
<h1>Proof graph</h1>
<p>Dependency graphs of the printed proofs in the October 18 manuscript
(<code>human_readable_main.tex</code>, paper commit {manifest()['sources']['paper']['commit'][:7]}). Comment
environments are excluded. Arrows run from premise to consequence. Results the paper cites,
and standard facts it uses without a citation, are drawn as axioms together with their source.
Click a node to jump to its proof graph or source.</p>
<ul class="legend">{legend}</ul>
<h2 id="overall">From the axioms to Theorem 1.1</h2>
<p>Roots are the three Lean base axioms and the external inputs. The three axioms sit under the
logic of every step of the paper. The Lean development proves Theorem 1.1 from these
three axioms alone; its route differs in places from the printed proof graphed here.</p>
<div class="fig bleed">{svg(overall_dot(), shrink=False)}</div>
<h2 id="proofs">One graph per proof</h2>
<p>Hypotheses enter at the top; the proved statement exits at the bottom. Theorem 3.7 (Gabber) and
Theorem 9.2 (Nullstellensatz) are stated without proof and appear as axioms.</p>
<div class="grid">{"".join(cards)}</div>
<h2 id="axioms">External inputs used as axioms</h2>
<div class="tbl"><table><thead><tr><th>Input</th><th>Source given</th><th>Used in</th></tr></thead>
<tbody>{"".join(rows)}</tbody></table></div>
<p class="mute">Generated by <code>scripts/build-proof-dag.py</code> from the manuscript snapshot in
<code>sources/paper/raw</code>. The graphs are a reading aid; they do not certify the printed proofs.</p>
</main>
</body></html>
'''


def manifest():
    return json.loads((root / 'manifest.json').read_text())


def refresh_checksums():
    sha = lambda b: hashlib.sha256(b).hexdigest()
    paths = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--cached', '--others',
                                     '--exclude-standard'], text=True).splitlines()
    paths = sorted(n for n in set(paths) if n not in {'SHA256SUMS', 'manifest.json'} and (root / n).is_file())
    m = manifest()
    m['files'] = {n: sha((root / n).read_bytes()) for n in paths}
    (root / 'manifest.json').write_text(json.dumps(m, indent=2, ensure_ascii=False) + '\n')
    paths.append('manifest.json')
    (root / 'SHA256SUMS').write_text(''.join(f'{sha((root / n).read_bytes())}  {n}\n' for n in sorted(paths)))


if __name__ == '__main__':
    (root / 'proof-dag.html').write_text(page())
    refresh_checksums()
    print(f'Wrote proof-dag.html: {len(ORDER)} proof graphs, {len(EXT)} external inputs.')
