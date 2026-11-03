# Section 3: paper findings

Sentences of Section 3 (paper itpplasma/stafford38-paper at c8f0d61, file
human_readable_main.tex) that look incomplete, imprecise or stronger than the
Lean step beside them. None affects the correctness of the Lean proof.

## Lemma 3.5, first paragraph: order N is claimed too early

- Card: `lem:order-symbol`, proof sentence at line 491.
- Paper: "Thus $\tilde d$ has order $N$, and its order-$N$ part is a $k$-linear
  combination of $\partial^\beta$ with $|\beta|=N$, ..."
- Lean: `obtain ⟨hF, hfibre, hhom⟩ := step_3_5_fibre k hdeg` gives only
  `dt ∈ orderPiece k (n + 1) N`; order exactly N is `step_3_5_order k hF hne`
  in the closing `exact`, with `hne : orderSymbol k N dt ≠ 0` from
  `step_3_5_pure_coefficient`.
- Why: the first paragraph shows only order at most N. That the order-N part is
  nonzero follows from the second paragraph (coefficient 1 of $\partial_1^N$).

## Proposition 3.2, final paragraph: symbol indices in the display

- Card: `prop:monic`, proof sentence at line 430.
- Paper: "$\sigma_N^B(\tilde d)=\sum_{j+\deg_B a_j=N}\sigma_N^B(p)^{\,j}\,\sigma_N^B(a_j)$,"
- Lean: `step_3_2_leading`, through `principal_bernstein_p_pow_mul`:
  σ_N^B(p^j a) = ξ₁^j σ_{N−j}^B(a) for a ∈ B_{N−j}.
- Why: the factors are σ_1^B(p)^j and σ_{N−j}^B(a_j); σ_N^B(p) and
  σ_N^B(a_j) are zero for N > 1 and j > 0. The display also ends in a comma
  followed by a capitalised "For".

## Proposition 3.2, final paragraph: a_j = 0 for j > N

- Card: `prop:monic`, proof sentence at line 426.
- Paper: "we have $\deg_B a_j\le N-j$ for all $j$; in particular $a_j=0$ for $j>N$"
- Lean: `step_3_2_decomposition` (from `exists_bounded_decomposition`) sums over
  j ≤ N only and states `bernsteinDegree k (a j) ≤ N - j` with natural
  subtraction.
- Why: for j > N the bound N − j is negative, so "a_j = 0" relies on the
  unstated convention deg_B 0 = −∞. The equality N = max_j (j + deg_B a_j) is
  not needed and not proved in Lean.

## Lemma 3.1, second paragraph: ω(w, w) = 0 is used without comment

- Card: `lem:sympcompl`, proof sentence at line 347.
- Paper: "if $a\neq0$, $\omega(av+bw,w)=a\neq0$"
- Lean: Lean-added step `have hAlt := alternating_of_antisymmetric ω hanti`.
- Why: Definition 2.8 calls ω symplectic when it is antisymmetric; ω(w, w) = 0
  follows only because 2 is invertible in k (characteristic zero).

## Proposition 3.6, proof: I for 𝓘

- Card: `prop:charP`, proof sentence at line 518.
- Paper: "(because $\tilde d \in I$)"
- Lean: `firstGenerator_mem` inside `step_3_6_kills`, membership in `idealI k N dt`.
- Why: the ideal is 𝓘 of (3.2).
