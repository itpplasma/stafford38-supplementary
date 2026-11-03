# Section 6: paper findings

Sentences of Section 6 of `human_readable_main.tex` (itpplasma/stafford38-paper
at c8f0d61) that look incomplete or less precise than the Lean step beside
them. None of them is an error in the result; the Lean proofs close every gap
listed here. The paper is not edited.

## 1. Lemma 6.2: the "in particular" clause has no argument

- Card: Lemma 6.2 (`lem:base-change`).
- Paper: "In particular, $\Char(Q_K)$ is the preimage of $\Char(Q)$ under
  $\Spec K[x,\xi]\to\Spec k[x,\xi]$."
- Lean: `Stafford38.Paper.Section6.step_6_2_char`
  (`rw [Section2.Char_eq, Section2.Char_eq, V, V, PrimeSpectrum.preimage_comap_zeroLocus, step_6_2_annihilator, Ideal.map, PrimeSpectrum.zeroLocus_span]`).
- Why: the printed proof ends with $Q=0\iff Q_K=0$ and never derives the
  statement about $\Char$. It follows from the annihilator equality because
  the zero locus of an extended ideal is the preimage of the zero locus; one
  sentence would close the gap.

## 2. Proof of Theorem 1.1: the case $\deg_B d=0$ is not mentioned

- Card: Proof of Theorem 1.1 (`proof:thm-main`), first sentence.
- Paper: "Let $d\in A_n(k)$ be nonzero of Bernstein degree $N$ and let
  $\tilde d=c^{-1}\Phi_g(d)$ be its monic normal form
  (Remark~\ref{rem:transport})."
- Lean: `Stafford38.Paper.Section6.theorem_1_1_paper`, step `· exact h`
  (the `deg_B d = 0` branch of `Section3.section_3_reduction`).
- Why: the monic normal form exists only for $N\ge1$ (Proposition 3.2).
  The case $N=0$ is settled at the start of Section 3, but this proof, which
  otherwise restates its setting, does not say so. The citation also points
  to Remark 3.3, while the normal form is Proposition 3.2.

## 3. Corollary 6.3, stable cyclicity: $F$ depends on the chosen generators

- Card: Corollary 6.3 (`cor:cyclic`), sentence "Since $t_1, t_2$ were
  arbitrary generators, for $l = 1$ we can set $a_1 = t_1, a_2 = t_2$ and
  choose $f_1 = -F$, then $\phi(1, -F) = t_1 - t_2F$ generates $T$."
- Lean: `Stafford38.Paper.Section6.corollary_6_3_of`,
  `obtain ⟨d', hd', h₁', h₂'⟩ := step_6_3_common_annihilator hOre htorsion (a 0) (a 1)`
  and `refine ⟨fun _ => -F', ?_⟩`.
- Why: $F$ was built from a common annihilator $d$ of the pair $t_1,t_2$
  obtained from Stafford's theorem. For a given generating pair $a_1,a_2$
  the argument has to be rerun with a common annihilator of $a_1,a_2$, giving
  a new $F$; "$t_1,t_2$ were arbitrary generators" says this only implicitly.
  The argument above it uses nothing about $t_1,t_2$ except that they
  generate $T$, so the claim holds as Lean proves it.

## 4. Corollary 6.3: "the annihilators of $t_1$ and $t_2$"

- Card: Corollary 6.3 (`cor:cyclic`).
- Paper: "Specifically, let us denote with $d_1$ and $d_2$ the annihilators
  of $t_1$ and $t_2$".
- Lean: `Stafford38.Paper.Section6.step_6_3_common_annihilator`,
  `obtain ⟨d₁, hd₁, h₁⟩ := htorsion t₁`.
- Why: $d_1,d_2$ are nonzero elements with $t_1d_1=t_2d_2=0$, not the
  annihilators (which are right ideals). Wording only.
