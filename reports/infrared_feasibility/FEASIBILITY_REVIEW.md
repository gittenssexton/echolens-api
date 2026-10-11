# EchoLens Gaia–WISE–2MASS feasibility results

**Run:** infrared-feasibility-v02. **Stage:** development/data readiness; not a frozen hypothesis test.

All 200 target/survey requests completed and were validated. Native responses retain all 298 AllWISE and 64 2MASS fields, with field metadata, queries, timestamps, hashes and original missing/limit flags. All 100 outcomes are retained.

| Stratum | Sources | WISE sole / ambiguous / unmatched | 2MASS sole / ambiguous / unmatched | Joint W3 + J/H/Ks screen |
|---|---:|---|---|---:|
| reference | 40 | 35 / 0 / 5 | 40 / 0 / 0 | 4 |
| other | 40 | 4 / 0 / 36 | 11 / 0 / 29 | 0 |
| variable | 20 | 14 / 0 / 6 | 15 / 0 / 5 | 1 |

**5 of 100 selected sources pass the joint preliminary W3 and three-band 2MASS screen**, including neighbor and catalog-source reuse checks. This is operational readiness, not validated counterpart identity, independent ordinary-star classification, or an infrared-excess result.

## What this establishes

The reproducible acquisition and replay path works for this selected mixed cohort. This first test measures availability and quality; no stellar-atmosphere model is fitted and no infrared residual, significance level or technological interpretation is computed.

The group design deliberately includes different Gaia-quality/variability strata. These 100 sources are not a representative occurrence-rate sample. VARIABLE is a catalog label; absence of that label does not establish constant brightness.

Only four provisional references and one catalog VARIABLE source pass the joint screen; no other-stratum source passes. Infrared coverage and quality sharply limit this selection. This pilot does not support a calibrated population test or an occurrence-rate estimate. The variable source particularly needs review of noncontemporaneous photometry. The five-source review queue is for association and model feasibility, not anomaly ranking. Preserve the current selection and treat any later selection changes as a separately versioned development design.

## Remaining scientific gates

Geometric matching uses epoch-aware direction-only proper motion, retaining multiple alternatives. It does not yet calculate combined positional covariance, chance-association likelihoods, annual parallax or perspective acceleration. Stationary WISE epochs and the year-2000 2MASS search center are approximations; catalog omissions, high motion and unresolved neighbors limit completeness. No image-based identity or contamination review has been performed.

Next, inspect the joint-screen sources and alternatives in survey images, calculate covariance-aware association assessments, and verify ordinary/reference labels. Then fit optical/near-infrared photospheres with W3/W4 held out and examine model predictive checks on development data. Sources in this run are development-exposed and cannot be silently reused as untouched holdout sources.

Six sources overlap the separate reference-only Experiment 001B (6 measured overlap). This is not independent confirmation. Both experiments preserve their selection identities.

## Validation and reproduction

35 local tests passed (one dependency deprecation warning); GitHub CI passed for code commit cc6bc70b45ed5672f82217603cc69640506990e4, run 38143064162. Two offline replays were compared byte-for-byte. All 200 response manifests and both metadata manifests passed checksum validation. No API/service settings were changed; draft PR #7 remains unmerged.

From the included repository-compatible files, install requirements and run `python -m scripts.infrared_feasibility --replay`. Place the archived `reports/infrared_feasibility` tree at the same relative path; the frozen 100 Gaia records are included in selection.json, so replay does not need another Gaia download or the entire Gaia database.

Full alternatives and original catalog values: results.json. Counts: summary.json. Selected inputs: selection.json. Response provenance and native FITS: raw/. Field descriptions/units: metadata/. Original acquisition errors: acquisition_errors.json.

References: https://irsa.ipac.caltech.edu/docs/program_interface/TAP.html ; https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html ; https://irsa.ipac.caltech.edu/data/2MASS/docs/releases/allsky/doc/sec2_2a.html

Research log: frozen mixed selection → native acquisition → schema/status/checksum validation → deterministic offline association/readiness replay → figures and audit archive. No anomaly ranking occurred.
