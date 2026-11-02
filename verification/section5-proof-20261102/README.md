# Section 5 proof update (2 November 2026)

The manuscript is unchanged: the frozen November 2 version, paper commit
`0dd6189bdf1bf2c670a8421cfc9952d5b6b811b9`, as recorded in
[manuscript-20261102](../manuscript-20261102/README.md).

The Lean sources move from formal commit `e2cf515` to
`97f1da4fd0244a9d390a2f60d7531d39a8927914`. In this version the Lean proof of
Theorem 5.7(i), `Stafford38.Paper.Section5.theorem_5_7_i_paper`, follows the
printed proof paragraph by paragraph. The place at infinity is built with
`lemma_5_9` and `lemma_5_10_place`. Each paragraph between the lemmas is a
declaration in `Stafford38/Paper/Section5/Steps.lean`, and the proof uses
Lemmas 5.11, 5.12(a), 5.12(b) and 5.13. Two steps are packaged differently
from the text. The invertible minor of M and the formula for ℓ are replaced by
a left inverse of M over κ[[t]]. The bound m ≤ d′+1 is proved through the
Kähler rank of the function field.

The cards for Theorem 5.7, its proof and Lemmas 5.9–5.13 are rewritten
accordingly, and the Lean proof graph has one node per paragraph.
`formal-verify.log` is the repository verifier run on this commit: full build,
all solution and challenge roots, and the strict dependency guard of the four
terminal roots.
