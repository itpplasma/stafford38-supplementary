# Canonical-definition refactor

This directory contains the formal proof and webpage generator changes used by
the local review draft. The source commits are local and have not been published.

## Changes

The refactor removes **29 definition or abbreviation declarations** and adds
none. The count excludes the generated standalone challenge copies. Callers use
the canonical owners directly, and the logical proof modules remain separate.

The removed names cover the standard Weyl algebra, phase indices, relations,
generators, linear combinations, the fixed-source statement and degree,
commutators, monomial weights, Euler subrings, polynomial coefficient maps, and
first coefficients of arcs. The intrinsic Bernstein degree has one definition;
a theorem computes it through Mathlib's weighted degree on PBW normal form.

The earlier page indexed a small manually selected set of definitions and did
not resolve names introduced by `open`. That left existing declarations such as
`PresentedWeyl`, `MvPolynomial.weightedTotalDegree`, and
`Stafford.Reduction.Stafford38` without useful definition links. The revised
reader resolves plain and selected namespace opens, deduplicates canonical
definitions, and displays their repository. Preserved manuscript annotations
show current names; their original names remain available in tooltips.

## Review and reproduction

The local project verifier passed: 4,476 build jobs, 313 independent consumer
reports, 109 manuscript-linked canonical declarations, both dependency routes,
and a 37-declaration axiom audit. The generator has 77 passing tests and one
unavailable historical fixture skipped. Chromium checks cover definition clicks,
all 1,771 local source links, source ownership, offline loading, and mobile layout.
The final three-kernel comparison results are recorded in
[`verification.json`](verification.json), with their logs alongside it.

| Concept | Definition to review | Repository |
| --- | --- | --- |
| Standard Weyl algebra | `Stafford38Challenge.WeylAlg` | Stafford38 |
| Intrinsic Bernstein degree | `Stafford38FixedSourceChallenge.bernsteinDegree` | Stafford38 |
| Weighted polynomial degree | `MvPolynomial.weightedTotalDegree` | Mathlib |
| Stafford certificate for one element | `Stafford.Reduction.Stafford38` | Stafford38 |
| Ring commutator | `AlgebraicAnalysis.ringCommutator` | AlgebraicAnalysis |

The Git bundles contain the new commits and require the public base commits
recorded in `manifest.json`. The patches provide a readable review of the changes.
`scripts/rebuild.py` fetches the public bases and loads the bundled commits before
rendering the page.

The preserved manuscript and `docs/paper-route-alignment.json` are unchanged.
The public challenge and solution theorem names and propositions are preserved.

The canonical standard Weyl algebra is `Stafford38Challenge.WeylAlg`. It
specializes `Stafford.FreeWeyl` to the standard symplectic matrix. The iterated
Ore algebra remains a different representation, connected by a proved algebra
equivalence. Internal aliases such as `PresentedWeyl` are removed.

The isolated Palomar challenge files must contain inline definitions and import
Mathlib only. Their definition blocks are generated from
`Stafford38/ChallengeDefinitions.lean`; verification checks their exact equality.
They share one authoritative source for review.

`MvPolynomial.weightedTotalDegree` is imported from Mathlib.
`Stafford.Reduction.Stafford38` is this project's certificate predicate.
Both now have definition links and visible source ownership in the reader.
