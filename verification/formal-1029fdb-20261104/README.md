# Formal sync to 1029fdb (4 November 2026)

The manuscript is unchanged (paper commit `0dd6189bdf1bf2c670a8421cfc9952d5b6b811b9`). The Lean sources move
from formal commit `8c417b3a9f0043d85967059cc51a7bbec65ec6ec` to `1029fdb382eee06e7b59bcf32801f40931e2079a`
(Define A_{≥0} by the Euler grading and prove Lemma 4.2 positivity by Euler degree (#22)).

- `formal-verify.log`: the repository verifier `scripts/verify.sh` run on
  `1029fdb382eee06e7b59bcf32801f40931e2079a`, followed by the root and route lines of its dependency guards.
- `map-check.log`: every declaration named by a card exists at this commit in
  the file the card names, and its statement is unchanged since `8c417b3`
  unless listed as reviewed; every theorem of the comparator files and every
  `Stafford38.Paper` declaration added since `8c417b3` has a card.
- `reader-build.log`, `browser.json`, `paper-build.log` and
  `verification.json`: the reader build, the browser check of every card and
  the isolated build of the paper PDF.

Source pages, Lean references and both proof graphs are regenerated from the
pinned sources; the cards themselves are not re-reviewed by this update.
