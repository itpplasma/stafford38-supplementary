# Supplementary v0.2.0 release preparation

Updated 3 October 2026. Accepted inputs: paper origin P4 `4d19a183846beb50f37ad2b4e51e836a76ed8bac`, public snapshot S4 `2fde6c6311b9cc2e8b789649132ff87bdbcdb3d5`, formal release R `54c4f0c902bcd840e44eeba80686ef3fa0e7dc2b` (v1.3.0, DOI 10.5281/zenodo.23126868), and generator `40967b6740c2ceaf515a2fb47a5ca9571be6495f`. Formal core C2 is `12ae3cc49152672a48a96f13994314b65ae38197`.

## Verification evidence

- Core C2 passed the full Linux repository verifier (R1 job 3131801) and retained R2 targets. All four actual Palomar comparisons passed in R4. The 399-name T80 declaration audit passed; guard reported zero axiom/sorry/unsafe additions, zero children, no source swap or verification stops.
- Formal release R’s 1,163 tagged files were verified byte-for-byte against the formal archive, with zero extras, missing files or mismatches. The 656 core files match C2 exactly; this release/core congruence is distinct from the core proof receipt.
- The pinned generator’s 64 tests and browser oracles passed on the frozen map; the existing 57-card browser walk covers all guided cards, both challenge cards and both routes. No human-review conclusion is inferred from these machine checks.
- Paper compilation produced the accepted P4 PDFs with zero undefined citations, references or control sequences. `ESM_2.pdf` must remain byte-identical to `lean_proof_details.pdf`.

## Remaining review and artifact steps

Johanna’s manuscript review and Max’s whole-paper correspondence review remain pending. The final S4 map and P4 PDFs are being copied into this candidate. Then the controller will render `index.html`, calculate final manifest hashes and `SHA256SUMS`, build and inspect the ordered 16-member `ESM_1.zip`, and compare the published archive with the tagged tree. The supplementary DOI remains unassigned until that archive comparison passes. Historical supplementary v0.1.3 and formal v1.2.3 remain unchanged; formal v1.2.3 DOI `10.5281/zenodo.23080671` applies only to that historical source.
