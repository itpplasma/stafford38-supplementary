# October 18 manuscript refresh

The selected manuscript is `human_readable_main.tex` at paper commit
`8834966c58b41b8a7eb7af76f15d15f71d43af23` ("Update on Overleaf."). The
paper checkout is read only. The supplementary contains an exact source
snapshot, regenerated excerpts and a PDF compiled in an isolated checkout.
`main.tex` is the paper's entry-point wrapper, not a second manuscript.

The comparison has 58 cards covering all 36 active theorem-like statements.
Seven cards were added for localization, module support, its element-annihilator
criterion, the divisorial place, the residue field, the generic tangent space,
and the Nullstellensatz. Removed or commented-out statements no longer appear
as current cards. The full raw source remains available for provenance.

The revised conormal proof uses a divisorial valuation, residue-field
derivations, a Laurent generic tangent frame and polynomial specialization.
The previous complex closed-point and tilted-arc proof is now excluded by a
LaTeX `comment` environment. The formal endpoint still follows its pinned
SameWitness route. The generic/Laurent formal results are comparison material;
this update does not assert that the revised printed proof is verified step
by step. The Lean sources and historical kernel-verification receipts are
unchanged. Johanna's manuscript review and Max's correspondence review remain
pending.

Five findings are shown in the reader's Comparison notes:

- `MS18-REF-01`: an active reference to the old asymptotic-conormal theorem
  label is unresolved.
- `MS18-REF-02`: `def:conormal` is referenced after being placed in a comment
  environment; the same proof has some fibre/cotangent containment notation
  requiring review.
- `MS18-DUP-01`: support avoidance has two consecutive proofs.
- `MS18-ORDER-01`: the residue-field proof uses valuation facts established
  later in the theorem proof.
- `MS18-NOTATION-01`: the strict length proof changes radical-ideal names and
  localization subscripts.

These are review findings, not edits to the paper. The two unresolved
cross-references remain visible in the compiled paper PDF and are the only
expected reference warnings in the reader build. The formal proof-details
PDF is retained with its historical source scope.

The updated generator masks comment environments before indexing statements,
labels, equations and annotations. It produces local paper source pages,
validates the bundled manuscript bytes against SHA-256 hashes, and displays
the newly written comparison notes and findings. Its exact source delta and
Git bundle are retained here; the earlier generator bundle and verification
receipt remain under `verification/canonical-definitions`.

`verification.json` records the actual build, regression tests, browser
checks, PDF source/hash and paper-preservation checks. Historical checks are
not reused as evidence for the new manuscript. Rebuild with the commands in
the repository README.
