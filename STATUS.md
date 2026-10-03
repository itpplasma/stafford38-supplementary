# Supplementary v0.2.1 release status

Updated 3 October 2026. Frozen inputs: paper origin P6 `33138378368fdc9f7bcb50947ccc9889f40cac43`, public six-input snapshot S6 `0bb3aa929b931bf5d82d90f62d7508d3ae1dccc1`, formal release R131 `f9448d6307fa25aff9d9f94ce0a9c7f9b03e63ff` (v1.3.1, DOI `10.5281/zenodo.23127367`), and generator `40967b6740c2ceaf515a2fb47a5ca9571be6495f`. The formal core is C2 `12ae3cc49152672a48a96f13994314b65ae38197`.

## Verification evidence

- Core C2 passed the full Linux repository verifier and retained proof targets; all four actual local Palomar comparisons passed. The 399-name public declaration audit passed with zero unsafe additions, children, source swaps, or verification stops.
- Formal release R’s 1,172 tagged files were byte-verified; 654 protected proof/tool files match C2; formalization.yaml provenance and lakefile.toml package version are explicit metadata exceptions. This release/core congruence is separate from the core proof receipt.
- The current 57-card map and current-review ledger are pinned to P6/S6/R131. Relations compare proposed corrected review text; struck author-baseline errors remain recorded in historical findings. The current labels are 21 exact, 11 equivalent, 9 Lean-stronger, 8 partial, 8 n/a; routes are 18 same, 13 similar, 1 Lean-only, 25 n/a.
- The three actual P6 PDF builds exited 0 with no undefined citations, references, or control sequences. Their receipt is `docs/paper-review-pdfs.json`; `ESM_2.pdf` is byte-identical to `lean_proof_details.pdf`.
- Four local Palomar comparisons passed. The owner-reported online Palomar check is mechanically verified; its automated review and registration remain pending.

## Review and publication status

Johanna’s manuscript review and Max’s whole-paper correspondence review remain pending. The visible author proof and both unchanged challenge statements are preserved; mathematical proposals remain for human review. The main and alternative routes use the shared challenge statements. The v0.2.1 archive DOI has not been assigned in this prepublication packet. Historical v0.2.0, supplementary v0.1.3, and formal v1.3.0 and v1.2.3 records remain distinct and unchanged.
