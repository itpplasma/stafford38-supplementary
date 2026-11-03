# Paper-route update (3 November 2026)

The manuscript is unchanged: the frozen November 2 version, paper commit
`0dd6189bdf1bf2c670a8421cfc9952d5b6b811b9`, as recorded in
[manuscript-20261102](../manuscript-20261102/README.md).

The Lean sources move from formal commit `97f1da4` to
`8c417b3a9f0043d85967059cc51a7bbec65ec6ec`. In this version every numbered
statement of Sections 2–6 has a Lean declaration in `Stafford38/Paper/` that
states the printed claim, and each printed proof is assembled from one
declaration per paragraph that calls the declarations of the results it cites.
Theorem 1.1 is `Stafford38.Paper.theorem_1_1`; the main Palomar solution proves
the challenge through it, and the alternative solution keeps the earlier proof.
The Mathlib-only challenge also states Theorem 1.1 and Corollary 6.3 as printed
(`Stafford38Challenge.theorem_1_1`, `Stafford38Challenge.corollary_6_3`).

Every card now lists the paper-route declaration of its statement, then the
steps of its proof in printed order, then the results the proof cites. Where
Lean still differs from the printed text, the card says how. The Lean proof
graph runs through the paper-route declarations to Theorem 1.1.

`formal-verify.log` is the repository verifier run on the tree of this commit
(run on branch commit `6b3d8ee`, whose tree is identical to `8c417b3`): full
build, all solution and challenge roots, the strict dependency guard of the
earlier and the paper-route terminal roots, and the route checks showing that
the main solution reaches Theorem 5.8 of the paper route and neither earlier
endpoint, while the alternative solution reaches the earlier endpoint and not
Theorem 5.8.
