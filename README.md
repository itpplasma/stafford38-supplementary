# Stafford38 reviewer companion

This repository provides a frozen review bundle for “Stafford’s conjecture on cyclicity of torsion modules.” Open [index.html](index.html) in a browser to read the mapped paper and source links, without a Lean installation or private repository access. The [living review interface](https://itpplasma.github.io/stafford38-formal/) is a read-only comparison view; Overleaf remains the manuscript editing authority. This bundle freezes the revisions in [manifest.json](manifest.json). The annotated human_readable_main.pdf preserves the visible author proof and marked local proposals; the proof-details PDF explains the selected formal routes. This is a review edition.

Max reviews the whole paper proof and both Challenge/Solution comparisons. Johanna reviews the visible manuscript and its local mathematical proposals; a proposal remains pending until she accepts it. The formal theorem's verification receipt and Palomar record apply to their named source and theorem. For the paper-to-Lean scope and current status, consult the formal repository's paper-route-alignment.json. This bundle has no new final-source or DOI record.

## Journal files

Online Resource 1 (`ESM_1.zip`) contains the self-contained HTML review, exact map and source manifest, annotated paper and mathematical proof supplement. Online Resource 2 (`ESM_2.pdf`) contains the readable proof accounts. These PDF and ZIP formats, descriptive captions, and Online Resource citations follow the [Inventiones supplementary guidelines](https://link.springer.com/journal/222/submission-guidelines).

## Rebuilding

Run `python3 scripts/rebuild.py` to rebuild the frozen browser artifact from its pinned public source revisions and generator. Reading existing files requires no Lean or Node installation. Rebuilding uses the locked JavaScript dependencies; review source changes against the pins before updating the bundle.

The companion is separate from the reusable Apache-2.0 paper–Lean audit generator. Licenses and third-party notices are in LICENSES and NOTICE. Historical release records remain attached to their original sources.

## Archival

The [Apache-2.0 generator](https://github.com/itpplasma/paper-lean-audit) and this manuscript-specific companion have separate archives. The repository owner has confirmed that the Zenodo GitHub integration is enabled for this companion. The current v0.1.3 GitHub release remains a draft and is tied to the historical bundle with paper origin `093527797b85f4547e7a5be03556fa9725b6077c` and formal v1.2.3; it predates the restored current manuscript and has no supplementary DOI recorded. Prepare the next bundle after the full verification job and final source pins are complete. Publish a new immutable release, compare its Zenodo archive with the tagged release tree, and record its DOI only after that comparison succeeds. The formal-proof repository has its own existing Zenodo archive.
