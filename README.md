# Stafford’s Conjecture 3.8 — paper and Lean proof

## [Open the proof comparison →](https://itpplasma.github.io/stafford38-supplementary/)

Read 69 paper passages beside the pinned Lean results. The reader uses the
November 11 version of `human_readable_main.tex`, commit `8e294b7`.
All 46 theorem-like statements are represented. Paper source links
open the bundled, unmodified manuscript; search, annotations and review notes
work offline.

**Current manuscript review:** open [index.html](index.html). Every numbered
statement of Sections 2–6 is mapped to its own Lean declaration, and each card
lists the Lean steps of the printed proof in order and the results it cites.
Where Lean still differs from the printed text, the card says how. Theorem 1.1
and Corollary 6.3 are also stated as printed in the Mathlib-only Palomar
challenge. No review finding is open. Each Lean reference of the manuscript
names the declaration of its statement in `Stafford38.Paper`. See the
[manuscript records](verification/manuscript-20261111/verification.json) and the
[paper-route update](verification/paper-route-20261103/README.md).
The Lean sources are pinned to formal commit
1029fdb, which passes the repository verifier
([log](verification/formal-1029fdb-20261104/formal-verify.log)).
This review update has no new journal release or Zenodo DOI.

**Offline:** download this repository, unzip it, and open **index.html**.
Paper and project source pages are bundled. External library links require
internet access. The [v0.2.2 release](https://github.com/itpplasma/stafford38-supplementary/releases/tag/v0.2.2)
and its [Zenodo archive](https://doi.org/10.5281/zenodo.23132562) preserve the
earlier October 3 manuscript and retain their original citation metadata.

**Proof graph:** [proof-dag.html](proof-dag.html) draws one dependency DAG per
printed proof, with hypotheses entering and the statement exiting. An overall
DAG runs from Lean's three base axioms to Theorem 1.1. Cited results and
uncited standard facts appear as axioms with their sources. Regenerate it with
`python3 scripts/build-proof-dag.py`, which requires Graphviz.
[lean-dag.html](lean-dag.html) does the same for the Lean proof. Its edges are
computed from Lean's environment and contracted to the key declarations.
Mathlib, AlgebraicAnalysis and the Lean proof of Gabber's theorem appear as cited
inputs.

**Definitions:** [definitions.html](definitions.html) lists, for every definition
of the paper, its Lean form as printed, the definition the Lean proofs work
with, and the theorems connecting the two. It marks which printed definitions
are used directly and for which only an equivalence is proved, and it places
the geometric definitions of Section 5 in Mathlib and the project's geometry
modules. Which connecting theorems the proofs use is computed from Lean's
environment. Edit `definitions.json` and run
`python3 scripts/build-definitions.py --formal PATH`.

**Every Lean identifier is linked to its declaration.** This applies in the
proof comparison and in all bundled source pages. The links come from Lean's
own reference data (`.ilean`) of the built formal checkout, stored in
`verification/lean-references/references.json`, not from name matching.
Project and AlgebraicAnalysis declarations open bundled source pages. Mathlib and
Lean core declarations open their pinned GitHub source. Hovering or focusing a
link shows the declaration's doc comment and signature, and for a definition its
body. The previews are embedded in each page, so they also work offline. `rebuild.py` reapplies
the links. Regenerating the data needs a built checkout of the pinned formal
commit: `python3 scripts/extract-lean-references.py --formal PATH --global GLOBAL_PATH` and
`python3 scripts/build-lean-dag.py --formal PATH`.

[Updated paper PDF](human_readable_main.pdf) · [Formal proof v1.3.1](https://doi.org/10.5281/zenodo.23127367)

Exact sources, licenses and review scope are in [manifest.json](manifest.json).
Rebuild the HTML with `python3 scripts/rebuild.py` (Git, Python, Node.js and npm
required). The manuscript snapshot is bundled and checked by SHA-256; rebuilding
does not need access to the paper repository. `--source NAME=PATH` selects an
existing source checkout; `--skip-install` uses installed dependencies offline.
Run `node scripts/check-reader-cdp.mjs . /tmp/stafford-reader-check verification/manuscript-20261111/migration.json`
for browser checks; set `CHROMIUM_PATH` when Chrome is installed elsewhere.
Attribution: [NOTICE](NOTICE).
