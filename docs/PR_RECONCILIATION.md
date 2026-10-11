# PR #2 / PR #3 reconciliation — 11 October 2026

## Proposed consolidated implementation

Use [PR #2](https://github.com/gittenssexton/echolens-api/pull/2) as the registry
foundation. Incorporate the useful status endpoint and manual artifact-export
idea from [PR #3](https://github.com/gittenssexton/echolens-api/pull/3), using PR #2's
schema and frozen data. Preserve PR #3's successful acquisition as a separate,
quality-selected cohort. Do not cherry-pick its conflicting importer, API or schema.
Neither PR has been merged; no Render settings were modified. PR #3 remains open
as an independent implementation and acquisition reference, pending final review.

Compared heads: PR #2 `bc0b6028bbda144cff4ee8d2d887f3cd9932c594`;
PR #3 `5fdb162ff0ee5bc64b8187b3d9664bdfc88c98c4`.

| Area | PR #2 | PR #3 | Reconciliation |
|---|---|---|---|
| Observations | Frozen 10,000 sources; native FITS + metadata; 157 fields | Successful ESA CSV acquisition; 10,000 sources; 15 fields | Retain PR #2 as primary; archive PR #3 separately |
| Selection | Low random-index interval and stellar-classification probability ≥0.9; uncertain data retained | Different random-index interval; parallax SNR ≥5, RUWE <1.4, G/color present | Distinct cohorts; do not silently pool or relabel |
| Provenance | Original bytes, hashes, exact request, timestamp, field units/UCDs/descriptions | CSV/query hashes, ADQL, timestamps in SQLite | Preserve both acquisitions; primary API keeps full field metadata |
| Validation | Exact count, IDs, selection/order, errors, correlations, TAP status, checksums, atomic build; ESA spot-check | Count, duplicate IDs, finite numbers, coordinates; selection/error/order not enforced by importer | Keep stronger primary importer; independently audit actual PR #3 artifact |
| Database | imports/stars/observations/crossmatches/interpretations | ingestion_runs/stars with selected columns | Incompatible SQLite schemas; do not point one API at the other's database |
| API | `/stars`, detail, `/catalogs`; unavailable registry =503 | Search/detail plus `/stars/stats`; unavailable registry reported as zero | Add `/stars/stats` to primary, retain 503 on missing DB |
| Search parameters | `g_max`, `parallax_min`, etc.; limit ≤200 | `max_g_mag`, `min_parallax`; limit ≤500 | Clients must use PR #2 contract; no aliases added |
| Artifact workflow | Committed observations already replayable offline | Live ESA fetch and 30-day artifact | Add manual offline build/test/export to PR #2; avoid automatic network refresh |
| Tests at compared heads | 25 passed locally and GitHub CI | 5 passed locally and GitHub CI; live import succeeded | Extend primary route coverage; retain independent evidence for both |

## PR #3 data acquisition independently verified

Workflow run [38138969207](https://github.com/gittenssexton/echolens-api/actions/runs/38138969207)
succeeded. Artifact `11701313699` contains original CSV, SQLite and manifest;
its original retention expires 10 November 2026. The downloaded archive SHA-256
matches GitHub's recorded digest:
`54258e24cec25a2899ba282edcb501aabad0c2a65c2812186f926363ed9f46ae`.

Independent inspection checked all 10,000 unique source IDs, finite values,
available nonnegative error fields, sky bounds, exact query/CSV hashes, query
selection and ascending random-index order. Every database value in the 15 CSV
fields matches its parsed source value. SQLite integrity is OK and foreign-key
checks are clear. There are **zero overlapping source IDs** with PR #2's cohort.
Exact results and acquisition timestamps are recorded in
`reports/pr3_acquisition_validation.json`. The original ZIP is archived in the
user's Echo Lens Drive folder; it is not loaded into the primary registry.

PR #3's PR body stated the fetch had not run; that statement is now stale relative
to the verified artifact. Successful real acquisition does not make the cohort a
matched control group or supply missing position errors/covariances, flux errors,
catalog class probabilities or source-column metadata. Those must come from an
independent catalog re-query if this cohort is later migrated.

## Review and eventual migration

1. Review PR #2 with these incorporated additions. Keep production untouched.
2. Use the frozen offline workflow when an exported database is needed. Move
   artifacts to durable storage before their retention expires.
3. If retaining PR #3 sources in the primary system later, re-query all Gaia fields
   for the exact source IDs and store their cohort selection/provenance explicitly.
   Do not fabricate missing measurements or call the result the same pilot.
4. Update clients to PR #2's endpoint contract. Keep `ECHOLENS_DB_PATH` pointed at
   a primary-schema database; `data/echolens.sqlite` from PR #3 is incompatible.
5. Only after final review, retire the duplicate PR and separately approve any
   merge/deployment. No closure, merge or deployment is performed by this reconciliation.
