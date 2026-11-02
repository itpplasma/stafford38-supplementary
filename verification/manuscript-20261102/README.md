# November 2 manuscript refresh

The selected manuscript is `human_readable_main.tex` at paper commit
`0dd6189bdf1bf2c670a8421cfc9952d5b6b811b9` ("Describe the paper-to-Lean-to-paper
workflow in the AI appendix"), the frozen version. The paper checkout is read
only. The supplementary contains an exact source snapshot and a PDF compiled
in an isolated checkout (`paper-build.log`).

Only prose changed since the October 28 version. Section 1.2 now says that
the proof in Sections 3–6 follows the formal proof step by step and that the
text marks where the two routes differ, and the AI appendix describes how the
paper proof was rewritten from the checked Lean proof. No statement was added,
removed or renumbered; `references.bib` and `ai_review.tex` are unchanged.
`scripts/update-manuscript-20261102.py` recomputes the excerpt ranges, of
which only the appendix moved; the earlier scripts are unchanged.

Subsection 5.2 is remapped to the Lean module `Stafford38.Paper.Section5`,
which states each printed statement:

- Theorem 5.7: `theorem_5_7_i` and `theorem_5_7_ii`, proved through
  `AlternativeAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure`
  along the printed route (algebraic case, discrete valuation ring at
  infinity, Laurent generic point, matrix with a unit minor, lift of the
  1-coordinate row). The statement is recorded as equivalent: Lean takes the
  prime ideal I(Y) instead of Y. The terminal theorem
  `GeneralAsymptoticConormal.coordinate_axis_mem_smooth_fibre_closure` keeps
  the second, chart-based route and is listed as the alternative proof, with
  its key same-witness declarations only.
- Lemmas 5.9–5.13: `lemma_5_9`, `lemma_5_10`, `lemma_5_11`, the three
  declarations for 5.12(a), `lemma_5_12_b` and `lemma_5_13`, recorded as
  exact. Lemma 5.12 keeps the route “similar”, because Lean bounds dim Θ_y
  from below with derivations rather than with the Jacobian rank.

The formal proof of Theorem 5.7 does not call `lemma_5_9` and `lemma_5_10`;
it builds its discrete valuation ring from the same intermediate results with
an additional coefficient field. `witness_lemma_5_11` and
`witness_lemma_5_12_5_13` prove that this ring and its Laurent column satisfy
Lemmas 5.11–5.13. The cards say so, and the Theorem 5.7 cards keep the route
“similar” for this reason. The Section 1.2 card no longer says that Lemmas
5.9 and 5.13 lack an exact declaration; Lemma 4.7 still has none.

The four open editorial findings of the October 28 refresh are unchanged.
The paper build has no unresolved references or citations.
