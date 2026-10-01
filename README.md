# Stafford38 reviewer companion

**Working author-review snapshot.** Proposed red corrections and unresolved action boxes remain visible. This is supplementary review material for *Stafford’s conjecture on cyclicity of torsion modules*, Christopher Albert, Johanna Moser and Maximilian Philipp, Graz University of Technology. Corresponding contact: albert@tugraz.at. Intended journal: Inventiones mathematicae; no submission or acceptance is claimed.

For the current editing/review version, open https://itpplasma.github.io/stafford38-formal/ . This repository freezes one explicit manuscript and proof revision for download and archival.

1. Open `index.html` in a browser, or the hosted frozen snapshot. No login, private repository access, Node or Lean installation is needed to read it. The HTML embeds its rendering code and fonts.
2. Begin at “Challenge: meaning and soundness”. Check the field and characteristic assumptions, rank, nonzero input, quotient relations and factor order. Links open exact definitions, including Field and CharZero. The proved Solution endpoints supply the theorem evidence; deliberate sorry holes in Challenge templates do not.
3. Max reviews all 49 current mathematical correspondence cards, including exact matches, definitions, printed proofs and appendix results. Read the comparison accounts in `lean_proof_details.pdf` to distinguish mathematical gaps from implementation differences. Johanna reviews concrete text proposals. Six context/history cards are separate.
4. Export reviewer notes as JSON. Browser storage is local, not shared human approval. The frozen snapshot has no automatic live-version check; its header and manifest identify the revision. The living interface checks freshness before sign-off.

`human_readable_main.pdf` preserves proposed changes and status boxes for Johanna. `lean_proof_details.pdf` gives mathematical explanations and pinned declaration links for Max or a referee. A statement correspondence badge is a curated review assessment, not a kernel theorem. The checked Lean v1.2.3 archive has DOI [10.5281/zenodo.23080671](https://doi.org/10.5281/zenodo.23080671); Palomar certifies its separately scoped registered theorem.

## Journal files

Online Resource 1 (`ESM_1.zip`): self-contained interactive paper–Lean review, exact mapping and source manifest, readable proof supplement and annotated author-review paper PDF.

Online Resource 2 (`ESM_2.pdf`): mathematical accounts of the selected machine-proved routes, with correspondence qualifications and pinned declaration links.

These descriptions and filenames follow the journal’s [supplementary guidance](https://link.springer.com/journal/222/submission-guidelines): PDF for text, ZIP for collections, descriptive captions and explicit Online Resource citations. Before final submission, freeze the accepted manuscript, replace the working review snapshot and confirm the complete author list; keep exact source/version pins. The present bundle is review-ready, not an assertion of final author approval.

## Rebuild and archival

Run `python3 scripts/rebuild.py`. It fetches the public pinned source commits and generator commit, installs locked JavaScript dependencies, rebuilds `index.html` and checks source correspondence. Reading the existing files needs no build. The original Overleaf project is not required.

Enable `itpplasma/stafford38-supplementary` and `itpplasma/paper-lean-audit` at https://zenodo.org/account/settings/github/ before publishing their prepared GitHub releases. Use Sync now, then On for each repository. Tags and draft releases do not mint a DOI; a published release after activation is needed. Record the resulting version DOIs in CITATION.cff, manifest and manuscript citations. No new DOI is claimed yet. The existing formal-repo Zenodo connection is already active; enabling the private paper repository is unnecessary for this public companion.

The reusable [Apache-2.0 generator](https://github.com/itpplasma/paper-lean-audit) is separate from this manuscript content. Licenses and third-party notices are in `LICENSES` and `NOTICE`.

The selected paper proof and Lean now use the same reviewed route throughout. Max reviews the whole frozen correspondence; Johanna reviews the marked mathematical prose. Historical alternatives remain in source history and are outside this assignment. The pair certificate is supplementary; the main Palomar Challenge is unchanged. Readable proof notes are optional aids, not another review task.
