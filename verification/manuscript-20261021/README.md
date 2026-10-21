# October 21 manuscript refresh

The selected manuscript is `human_readable_main.tex` at paper commit
`204f5ea59c3feeba3375910c4e508e88d71cd3c3` ("Update on Overleaf."). The
paper checkout is read only. The supplementary contains an exact source
snapshot, regenerated excerpts and a PDF compiled in an isolated checkout.

The paper was restructured: Lean verification is now Section 1.2, the
vanishing-cokernel and characteristic-variety material is part of Sections 3
and 4, the conormal geometry is Section 5 with its lemmas stated inside the
proof, and "Generalizations and open questions" (Section 7) replaces the
Outlook and Further work. `scripts/update-manuscript-20261021.py` maps every
existing card to the new layout; `scripts/update-manuscript.py` is unchanged
and records the October 18 migration.

The comparison has 66 cards covering all 40 theorem-like statements. No card
was removed. Two labels changed: `cor:charP` is now Proposition 3.6
(`prop:charP`) and `lem:Uzero` is now Corollary 4.11 (`cor:Uzero`); the
cards keep their ids. The labels `def:conormal`, `def:divisorial`,
`def:proj-closure`, `def:smooth-conormal`, `lem:lift` and `lem:special`,
which were inside comment environments on October 18, have been deleted from
the source. Eight cards were added: Definitions 5.1 and 5.2, Lemmas 5.7 and
5.11, the separately printed proofs of Proposition 3.6 and Theorem 5.6, the
Section 5 overview, and generalization (b) of Section 7 with its pinned
repository `itpplasma/symplectic-stafford-formal` at `dccff0d`.
Generalization (a) keeps the Global Stafford card.

The Lean sources, their pins and the historical kernel-verification
receipts are unchanged. Comparison labels do not certify a revised printed
proof; Johanna's manuscript review and Max's correspondence review remain
pending.

Findings shown in the reader's Comparison notes:

- `MS18-REF-02`: the proof of Theorem 5.6 still references `def:conormal`.
- `MS18-NOTATION-01`: Lemma 4.10 still writes `I_p` once and mixes
  localization subscripts.
- `MS21-CITE-01`: the Section 5 overview cites the undefined key `idk`.
- `MS21-TODO-01`: the proof sketch reads "section XXX".
- `MS21-PROOF-01`: the proof of Proposition 3.6 is printed at the start of
  Section 6.
- `MS21-REF-03`: the conormal proof cites Lemma 5.10(c), now Lemma 5.11.
- `MS21-KAPPA-01`: Lemma 5.9 mixes index names and leaves "d′ = " unfinished.
- `MS21-DEF-01`: Definition 5.1 has an empty item and writes κ/K for L/K.

`MS18-REF-01`, `MS18-DUP-01` and `MS18-ORDER-01` are resolved in this
revision and kept as history. The unresolved `def:conormal` reference and
the `idk` citation are the only expected warnings of the reader and paper
builds.

The generator adds three commits on its October 18 branch: `\leanglobal`
and `\leanfiltered` references are checked against the pinned `global` and
`filtered` sources like `\leandecl`, a card may quote one clause of a long
`\AIadd` paragraph, and `\url` renders as a link. The source delta is in
`generator.patch`, the commits in `generator.bundle`. The proof graph and
the Lean proof graph use the new statement numbers; the Lean graph data in
`verification/lean-dag/graph.json` is unchanged.

`verification.json` records the build, regression tests, browser checks,
PDF source and hash, and paper-preservation checks.
