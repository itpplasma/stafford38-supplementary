# Supplementary release preparation

Status: paused at the owner's request on 2 October 2026; all owned agents and compiler jobs are stopped. Zenodo publication remains pending the final verified snapshot. The repository owner has confirmed that the Zenodo GitHub integration is enabled for `itpplasma/stafford38-supplementary`; the account setting itself is not publicly inspectable here.

## Historical bundle

- Companion version is `0.1.3`; the preparation checkpoint was `3ef18ca4cf1e422a13bb20514074503b8ca4671b`, and the `v0.1.3` tag points to `9576c3a1936795b1f9a2799ea60087d626decb87`.
- `manifest.json` records paper origin `093527797b85f4547e7a5be03556fa9725b6077c`, formal paper snapshot `bce92ec2d8ac53993b3edc568561a814ce5db518`, and formal source `ba18817c4cd4e5cfeab11da44ce76623f4c2b508` (signed v1.2.3, DOI `10.5281/zenodo.23080671`). This is the historical bundle; it predates the restored current manuscript.
- The manifest has `zenodo_version_doi: null`. The public GitHub API shows its v0.1.3 release as a draft with no publication date. Its uploaded ESM_1.zip and ESM_2.pdf digests match the local files, so those assets are also the historical snapshot.
- Exact Zenodo searches returned no public record for this companion. The available read-only tools cannot inspect the authenticated Zenodo–GitHub setting, so the armed state rests on the owner's confirmation.
- The README distinguishes the historical assets from the unfinished current proof. Documentation checksums were refreshed for the stopped checkpoint; the historical asset files and their source pins remain unchanged. Regenerate all release hashes when building the final new snapshot.

## Release gate

1. On resumption, complete the same-witness closure and terminal wiring, then finish the full formal verifier, Linux/Palomar comparisons and manuscript checks. Record the controller-selected final paper, formal, and generator commits; do not reuse the v0.1.3 pins.
2. Build the next review bundle from those exact public commits. Update the map, annotated manuscript, proof details, version, manifest, `.zenodo.json`, `CITATION.cff`, archive files, and checksums together. Keep the historical v0.1.3 records unchanged.
3. Run `python3 scripts/rebuild.py` from a clean checkout to rebuild and check the HTML against the exact pins. This script does not regenerate the PDFs or ESM_1.zip; rebuild those from the final sources and record their hashes separately.
4. Run the final paper compilation, formal repository verifier, required Comparator checks, declaration/source-link audit, layout checks, and archive-content checks. Retain commands, exit codes, source pins, and log hashes in the release evidence.
5. Prepare a new immutable version and draft using the attached release body. Check that its manifest, release tree, PDF/ZIP files, and GitHub assets all refer to the same snapshot. The current v0.1.3 draft is not the release candidate.
6. After the full gate passes, the controller may publish the new GitHub release. Then retrieve the Zenodo archive, compare its files with the tagged release tree, and record a DOI only after the byte comparison succeeds.

## Local release tooling

The companion provides `scripts/rebuild.py` for its public-source HTML rebuild and `.github/workflows/pages.yml` for Pages deployment; neither publishes a Zenodo archive. The formal repository's `docs/release-runbook.md` requires a clean verified source, a new signed immutable tag, archive comparison, and DOI recording only after publication. No release, tag, upload, or publication action was taken during this preparation.
