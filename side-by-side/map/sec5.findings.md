# Section 5: paper findings from the side-by-side mapping

Paper `itpplasma/stafford38-paper` at c8f0d61, `human_readable_main.tex`;
Lean `itpplasma/stafford38-formal` at 665fb5b. The paper is not edited; these
are notes for its authors. Card names are those of the reader built from
`sec5.json`.

## Claims that need a word more than the text gives

1. **Theorem 5.7, proof of (ii), the case deg G = 0.**
   Paper: "if $\deg G=0$, $G$ is a constant that vanishes somewhere, so $G=0$."
   A constant that vanishes on all classes $[\xi]$, $0\ne\xi\in N(Y)$, is zero
   only if such a class exists, i.e. $N(Y)\ne\{0\}$; the text does not say why.
   Lean: `step_dir_of_fibre`, `obtain ⟨v, hv, hv0⟩ : ∃ v ∈ smoothConormalFibreProjection I, v ≠ 0`,
   derives it from (i): if $N(Y)\subseteq\{0\}$, every $\xi_i$ vanishes on
   $N(Y)$, hence at $(1,0,\dots,0)$, which fails for $i=1$. One sentence would close it.

2. **Remark after Theorem 5.7 (`\AIadd`, `\formalref`).**
   Paper: "the formal proof follows the same route except for a transcendence
   argument in one sublemma". The paper-route Lean proof
   (`Stafford38.Paper.Section5.theorem_5_7_i_paper` and the declarations it
   calls) also differs in three other places:
   - Lemma 5.12(a): Lean proves $\dim\Theta_y=\dim_F\Omega_{F/K}$ by an upper
     bound (`PaperGenericTangentRank.generic_tangent_finrank_le_component_kaehler_finrank`)
     and a lower bound from the $K$-derivations of $F$
     (`component_kaehler_finrank_le_generic_tangent_finrank`), not by the second
     fundamental exact sequence for $K[x]\to R$ and localization.
   - Lemma 5.10: $V=A_{\mathfrak p_D}$ is shown to be a discrete valuation ring
     because it is a Noetherian valuation ring $\ne F$
     (`stage3_exists_height_one_prime_valuation`, Definition 5.3(b)), not
     through normality and dimension one.
   - First paragraph (x̄₁ algebraic): Lean puts $(y,dx_1)$ in the equation
     conormal locus at one point $y\in Y$ and reaches $N(Y)$ by the density
     argument of the final paragraph (`exists_constant_coordinate_equation_and_pure_axis`,
     `fibreLift_mem_vanishingIdeal_equationConormal`), so it never needs a
     smooth point or $c\ne0$.
   The remark also points to `Stafford38.Geometry.GeneralAsymptoticConormal`,
   the second (chart-based) route, rather than to the paper-route declarations.

## Typographical slips (no effect on the argument)

- Lemma 5.9, proof, first word: "ince" for "Since".
- Theorem 5.7, proof, paragraph after Lemma 5.11: "$q'_i(t) = \sum_rr\,c_rt^{r-1}$"
  should read $c_{ir}$.
- Theorem 5.7, proof, definition of $y$: "in affine coordinates. its
  coordinates" (lower-case sentence start).
- Lemma 5.10, proof: "$x_1$ is a nonzero nonunit of $W$" for $\bar x_1$;
  "$V_K(p, x_1)$" and "$1=p+gx_1$ for some $p\in\mathfrak p$" reuse $p$ for
  the ideal and an element.
- Theorem 5.8, proof: "applied to a $a \in J$" for $g\in J$; "a polynomial it
  $t$" for "in $t$"; "Remembering the definition of $\phi$" for $\varphi$;
  "elemens"; "$g(y, dh_y = G(y) = 0$" lacks a parenthesis; the first two
  sentences and the outline both suppose $W\ne\varnothing$.
- "Corr." for "Cor." in two citations of Atiyah–Macdonald.
