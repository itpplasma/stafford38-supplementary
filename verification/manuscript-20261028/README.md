# October 28 manuscript refresh

The selected manuscript is `human_readable_main.tex` at paper commit
`498a741686012734832547d9f33705130a37d218` ("Update on Overleaf."). The
paper checkout is read only. The supplementary contains an exact source
snapshot, regenerated excerpts and a PDF compiled in an isolated checkout.

The preliminaries were rewritten. Subsection 2.1 is replaced by numbered
definitions, Definition 2.5 of October 21 is split into the symplectic form
(Definition 2.8) and the Poisson bracket (Definition 2.9), the
Nullstellensatz gains a closed-point clause, and Section 5.1 adds
definitions of valuation rings and of the conormal space. Every printed AI
proposal is resolved in the text; only the `FV-03` placeholder comment
remains. `scripts/update-manuscript-20261028.py` maps every card to the new
layout; the October 18 and October 21 scripts are unchanged.

The comparison has 69 cards covering all 46 theorem-like statements.

- Added (5): Definitions 2.1 (`def:cyclic`), 2.6 (`def:spec`), 2.9
  (`def:poisson`), 5.3 (`def:valuation`) and 5.4 (`def:conormal`).
- Relabelled (2): the card `cotangent` is now Definition 2.5
  (`def:cotangent`), and `def:symplectic-poisson` is Definition 2.8
  (`def:symplectic`); the cards keep their ids. The labels `sec:cotangent`
  and `def:symplectic-poisson` no longer exist.
- Removed (2): `prop:charP-proof`, because the proof of Proposition 3.6 now
  follows the statement and belongs to its card; `appendix-right-ore`,
  because Section 7 no longer lists the identity in every right Ore
  localization.
- Renumbered: Section 2 statements from 2.1 onward, Definitions 5.3–5.4 to
  5.5–5.6, Theorems 5.5–5.6 to 5.7–5.8 and Lemmas 5.7–5.11 to 5.9–5.13.
  `migration.json` lists the map. Notes in existing cards use the new
  numbers; historical findings keep theirs.
- Notation 2.2: the `convention` environment now prints “Notation”.

The Poisson-bracket notes of earlier cards said Lean's bracket is the
negative of the paper's. The printed bracket is
Σᵢ (∂f/∂xᵢ · ∂g/∂ξᵢ − ∂f/∂ξᵢ · ∂g/∂xᵢ), which is Lean `poissonBracket` with
the same sign; the new cards say so. Lean `phasePairing` is −ω.

Findings shown in the reader's Comparison notes:

- `MS21-DEF-01` (partly resolved): the empty item is gone, but Definition 5.1
  still defines algebraic, finitely generated and separable extensions for
  κ/K inside a definition about L/K.
- `MS28-REF-01`: Section 7 no longer lists the right Ore localization, but
  its Lean reference still cites `s38_rightOreLocalization`.
- `MS28-TYPO-01`: Notation 2.2 reads “… on A_{n−1}(k). so that x₁ is
  central”.
- `MS28-FIELD-01`: Theorem 2.11 is over K but writes √Ann_{k[x,ξ]} gr M.

Resolved in this revision and kept as history: `MS18-REF-02`
(`def:conormal` exists again), `MS18-NOTATION-01`, `MS21-CITE-01` (the
`idk` citation), `MS21-TODO-01`, `MS21-PROOF-01`, `MS21-REF-03` and
`MS21-KAPPA-01`. Thirteen proposed changes awaiting author acceptance are
moved to history, since their AI markup is no longer in the manuscript;
this records the markup's removal, not an acceptance decision. The reader
build and the paper build have no unresolved references or citations.

The proof graph uses the new numbering and the new citations: the
Nullstellensatz, the Weyl-algebra basics, the Ore property, the density of
the smooth locus and the Kähler-differential facts are now cited inputs;
finite length at a minimal prime (Lemma 4.8) is argued instead of being an
unsupplied input; and the conormal space is Definition 5.4. The Lean proof
graph data in `verification/lean-dag/graph.json` is unchanged; only its
paper labels are renumbered.

The Lean sources, their pins and the historical kernel-verification
receipts are unchanged. The generator is unchanged at `7c0b67c`. Its
regression suite was not rerun for this refresh. `verification.json` cites
the October 21 run at the same commit
(`verification/manuscript-20261021/generator-tests.log`). Comparison labels
do not certify a revised printed proof; Johanna's manuscript review and
Max's correspondence review remain pending.

`verification.json` records the reader build, browser checks, PDF source
and hash, and paper-preservation checks.
