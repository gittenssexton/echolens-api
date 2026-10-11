# EchoLens registry post-merge audit — 2026-10-11

## Verified GitHub state
- Default branch: `main`, audited HEAD `95b3f8ea401fc7415fe5254c17f09326057c00a9`.
- PR #2 is **merged** and is the canonical primary Gaia DR3 stellar registry. PR #3 is superseded as an implementation but its separately acquired 10,000-star cohort remains archived and **must not be silently pooled**.
- Primary registry preserves a frozen selection of **10,000 actual Gaia DR3 stars**, reported 157 fields, original native FITS bytes, companion VOTable field metadata, source IDs as strings, uncertainties, correlation fields, query, retrieval provenance and checksums.
- Registry has atomic/offline importer in `scripts/import_gaia.py`, `app/registry.py`, `app/main.py`, tests and GitHub Actions. Exposed routes: `/`, `/health`, `/stars`, `/stars/stats`, `/stars/{source_id}`, `/catalogs`.
- `data` retains immutable catalog snapshots for offline rebuilding; generated SQLite is excluded from Git. **A passing health endpoint does not prove the serving deployment has a populated registry**. Check `/stars/stats` explicitly, where an absent DB yields HTTP 503.
- Original registry PR states 26 local tests passed and describes prior CI; this audit does **not** claim to have rerun those tests.

## Follow-on work already under review (do not duplicate)
- PR #5 (Experiment 001A): only 3/100 non-reference targets matched the provisional reference pool within preregistered tolerances. Thus reference coverage failed its operational threshold; do not rank anomalies with these controls.
- PR #8 (Experiment 002A): conditional within-screen overlap; not an independent normal-star control.
- PR #6 and stacked PR #10: AllWISE 100-target pilot and strict offline replay/display rounding correction. Provisional associations are not confirmed counterparts or infrared excesses.
- PR #7: mixed Gaia–WISE–2MASS feasibility pilot, not a confirmed infrared-excess search.
- PR #9 and stacked PR #11: 250 LAMOST observations, independent Gaia ID audit, and unverified observation-epoch astrometric association gate. Spectroscopic pilot is brightness-selected and does not establish ordinary controls.
- Existing branch `research/f01-selection-bias-20261011` is ahead of `main`; coordinate selection-bias work there before starting an overlapping analysis.
- PR #4: research website. None of these experimental PRs is assumed deployed.

## Scientific decision gates
1. **Primary hypothesis.** H0: apparent electromagnetic outliers follow natural populations, dust/extinction, multiplicity, instrumental/selection effects and measurement noise; H1: reproducible departures remain after registered null models. Even H1 is *not* evidence of artificial origin on its own.
2. **Unbiased comparisons.** Define target and reference sampling frames, covariate overlap diagnostics, completeness/selection function, astrometric quality, extinction/crowding, magnitude and SNR; freeze thresholds before outcome inspection. Never label the provisional 531-star Gaia quality screen or bright LAMOST cohort 'verified lifeless controls'.
3. **Real observation integrity.** Preserve immutable upstream artifacts and checksums, release, query, UTC retrieval, native units, uncertainties/covariance, quality masks and nulls. Catalog stellar parameters belong in catalog-inference fields; fitted residuals in derived analyses; language-model suggestions in separate interpretations. Never backfill absent errors or promote matches without evidence.
4. **Cross-survey association.** Propagate Gaia positions to actual observing epochs and propagate astrometric uncertainties; retain all candidate associations and ambiguity flags. Do not treat J2000 reference coordinates as an observation epoch.
5. **Statistical registration.** Freeze training/calibration/test group allocations and leakage groups, models, tests, multiple-testing correction, injections and negative controls *before* a confirmatory search; evaluate detection completeness, sensitivity and false discovery using held-out data.
6. **Review before release.** Test data integrity, independent source comparison, reproducibility and negative controls; hold unmerged research branches until their parent/dependencies and artifact retention have been reviewed.

## Deployment / merge separation
This audit is documentation-only and changes no importer, data, application endpoints, database schema, workflows or Render configuration. A new production deployment requires separate approval and verification that the SQLite registry is populated. Until then, distinguish the `main` repository's features from what the Render instance serves.

## Historical correction
`docs/PR_RECONCILIATION.md` describes the *pre-merge* evaluation and contains accurate historical references such as 'Neither PR has been merged'. Those are not the current GitHub state. See merged PR #2 as the current record.
