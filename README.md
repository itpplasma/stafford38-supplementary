# Stafford’s Conjecture 3.8 — paper and Lean proof

## [Open the proof comparison →](https://itpplasma.github.io/stafford38-supplementary/)

Read 58 paper passages beside the pinned Lean results. The reader uses the
October 18 Overleaf update of `human_readable_main.tex`, commit `8834966`.
All 36 active theorem-like statements are represented. Paper source links
open the bundled, unmodified manuscript; search, annotations and review notes
work offline.

**Current manuscript review:** open [index.html](index.html). Expanded support,
divisorial and Laurent-tangent arguments are mapped explicitly; commented-out
proofs are excluded. Five findings, including two unresolved references in the
paper, are recorded in Comparison notes. See the
[update and verification records](verification/manuscript-20261018/README.md).
The paper has not been edited. The Lean source pins and their
[canonical-definition verification](verification/canonical-definitions/README.md)
are retained; they do not certify the revised printed proof step by step.
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

**Every Lean identifier is linked to its declaration.** This applies in the
proof comparison and in all bundled source pages. The links come from Lean's
own reference data (`.ilean`) of the built formal checkout, stored in
`verification/lean-references/references.json`, not from name matching.
Project and AlgebraicAnalysis declarations open bundled source pages. Mathlib and
Lean core declarations open their pinned GitHub source. `rebuild.py` reapplies
the links. Regenerating the data needs a built checkout of the pinned formal
commit: `python3 scripts/extract-lean-references.py --formal PATH` and
`python3 scripts/build-lean-dag.py --formal PATH`.

[Updated paper PDF](human_readable_main.pdf) · [Archived formal proof details PDF](lean_proof_details.pdf) · [Formal proof v1.3.1](https://doi.org/10.5281/zenodo.23127367)

Exact sources, licenses and review scope are in [manifest.json](manifest.json).
Rebuild the HTML with `python3 scripts/rebuild.py` (Git, Python, Node.js and npm
required). The manuscript snapshot is bundled and checked by SHA-256; rebuilding
does not need access to the paper repository. `--source NAME=PATH` selects an
existing source checkout; `--skip-install` uses installed dependencies offline.
Run `node scripts/check-reader-cdp.mjs . /tmp/stafford-reader-check` for browser
checks; set `CHROMIUM_PATH` when Chrome is installed elsewhere.
Attribution: [NOTICE](NOTICE).
