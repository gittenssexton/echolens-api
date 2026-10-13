# EchoLens fresh comparison cohort and calibration development v0.10–v0.11

2026-10-13 UTC. Runs `independent-selection-readiness-v10` and `calibration-development-v11`. Development work only; no production registry/API/Render change and no confirmed technosignature claim.

## Result

Selected **20 new comparison candidates using Gaia alone**, outside the primary 10,000-source acquisition's random-index domain, with no overlap with the exposed v0.2 cohort. The selection and development/reserved roles were frozen before infrared retrieval. Complete native observations are preserved.

**16 of 20** pass the operational joint J/H/Ks and W3 readiness screen: nine development stars and seven reserved validation stars. Four flagged cases stay in the frozen cohort, without replacement. These remain provisional stellar comparisons, not certified ordinary-star controls.

The nine development stars were fitted with J/H/Ks only, using dense PHOENIX spectra. Across six conditional cases per star (54 fits), W3 residuals span **−2.83% to +4.87%**. At Rv=3.1, raw Gaia central parameters give a median residual **+0.149%**, versus **+0.373%** using the published field-star parameter calibration sensitivity. This supports small development residuals with the corrected pipeline; it does not establish a calibrated null distribution or false-positive rate.

**No reserved validation star was predicted or scored.** Raw observations are archived, so these roles are policy reservations from fitting/tuning rather than technical blinding.

## Prospective selection and acquisition

Initial request: TOP100 Gaia main/AP join ordered by Gaia random_index, selecting sources with random_index≥1,000,000. An ADQL `!=` syntax error was corrected to `<>`, and the main source-ID field was aliased to avoid a duplicate join name, before any valid response/selection. The synchronous query returned a native timeout. The equivalent asynchronous request continued running and was aborted. A documented performance amendment bounded random_index to **1,000,000–100,000,000**, with the physical/quality cuts unchanged and before obtaining a valid pool or infrared data. That asynchronous query completed and returned **100 valid sources**.

A separate main-table seed-query alternative timed out and supplied no data or selection. Its attempted query is recorded, but it is not the source of this cohort. Error responses and asynchronous provenance are retained. An IRSA schema lookup also verified that Gaia DR3 AP mirrors exist; no mirrored AP measurements are substituted here.

Gaia-only cuts:

- |Galactic latitude|>20 degrees; G between 8 and 13; RUWE<1.2; duplicated_source=false; non_single_star=0; no catalog VARIABLE flag; five-parameter astrometry (astrometric_params_solved=31); parallax/error>10; DSC combined single-star probability>0.99.
- GSP-Spec's first 13 quality-flag characters are zero.
- Published 16th/84th-percentile bounds lie inside the currently available model box: Teff 4900–5200 K, logg 2.5–3.5, [M/H] −0.5–0.0. Median ordering and all constraints are rechecked locally.

Gaia random_index is an acquisition ordering, not a claim that the final quality-filtered sample represents all stars. The narrow stellar-parameter, latitude, brightness, astrometry and spectroscopy requirements impose strong selection biases. This cohort is suitable only for developing methods in that limited regime.

Exclude the 100 exposed v0.2 source IDs explicitly. Rank the remaining pool by SHA-256 of `echolens-calibration-v10:` plus each exact source-ID string, then numeric source ID. Freeze the first 20; the first 12 are `calibration_development`, and the remaining eight are `validation_reserved`. No WISE/2MASS magnitude, detection or residual enters that ranking. W3-based measurement-quality conditioning occurs later and can bias residual distributions near detection limits; it must be modeled before inferential calibration.

Preserved Gaia data: native 100-row main/AP pool with **243 fields**, including the complete 226-field AP record and selected main fields; and a separate exact-ID acquisition of all **152 main fields** for the chosen 20 stars. The duplicate main/AP stellar-probability column is explicitly renamed in the parsing adapter, with both values retained; original native bytes remain unchanged. Exact 64-bit IDs and field metadata are retained.

## Infrared readiness

All **40 target requests** (20 AllWISE and 20 2MASS) completed and validated, alongside two native field-metadata queries. Preserve all 298 AllWISE and 64 2MASS fields, original FITS, query URLs/epochs/hashes, all returned alternatives, flags and null/limit values. Validated trailing zero-filled transport padding is distinguished from astronomical rows. No duplicate extraction is silently treated as a separate star.

Retrieve 15-arcsec cones after direction-only Gaia proper-motion propagation. Matching uses the documented approximate survey epochs and individual 2MASS observation dates, with a 3-arcsec geometric eligibility radius. All 20 stars have sole geometric associations in both catalogs. These are provisional identities; no covariance-qualified acceptance, annual parallax/perspective model or full image/contamination review has been completed for this new cohort.

Band screens reuse the archived v0.2 rules: 2MASS A quality, no confusion flag and positive combined magnitude errors for J/H/Ks; W3 A/B quality, SNR≥5, positive magnitude/flux errors, no W3 artifact flag, ext_flg=0, no reported saturated fraction. A catalog neighbor within 6 arcsec or reused extraction prevents operational readiness. W1/W2 have their own separate band gates. Upper limits are retained, not fitted as Gaussian measurements.

| Readiness | Count |
|---|---:|
| Frozen candidates | 20 |
| J/H/Ks ready | 19 |
| W3 ready | 17 |
| Joint ready | 16 |
| Development joint-ready | 9 of 12 |
| Reserved validation joint-ready | 7 of 8 |

Flagged retained sources:

| Gaia ID | Role | Principal issue |
|---|---|---|
| 4674747172106182016 | Development | AllWISE extended-source flag; other band issues also retained |
| 39181169872636544 | Development | 2MASS H quality below A |
| 5758643673181721216 | Development | Another AllWISE object within 6 arcsec |
| 1427866279897798528 | Reserved validation | W3 artifact flag |

## Gaia parameter calibration context

ESA states that published GSP-Spec gravity and metallicity are deliberately uncalibrated. Preserve raw values. As a sensitivity, use the published generic field-star corrections from Recio-Blanco et al., both evaluated using **raw** logg x:

```
logg_cal = logg + 0.4496 - 0.0036*x - 0.0224*x*x
MH_cal   = MH + 0.274 - 0.1373*x - 0.0050*x*x + 0.0048*x*x*x
```

The open-cluster metallicity prescription is not used. The archived official page gives the equations and cautions about reference/model biases. No correction is treated as exact ground truth or used to revise cohort membership.

All 20 calibrated central estimates remain in the current model box. Nineteen transformed parameter-box envelopes fit within it; one extends beyond and stays flagged. The metallicity envelope includes polynomial extrema as well as endpoint combinations. It is a rectangular sensitivity envelope, not a joint confidence interval; correlations and correction uncertainty are not represented. No parameter is clipped to a template boundary.

## Development fits

Freeze the v0.11 method after readiness assessment and before computing residuals. Use only the nine joint-ready development stars. Fit J/H/Ks with archived native PHOENIX spectra, using the same theoretical grid and CALSPEC/SVO/G23 framework validated in v0.7–v0.9. Include native model/filter/Vega knots plus the auxiliary quadrature grid. The sparse CK04 linear-FLAM method that caused v0.6's false W3 discrepancy is not used.

Each star has six cases: raw median parameters or the generic logg/MH sensitivity, crossed with Rv=2.5/3.1/4.0. Teff is the raw GSP-Spec median. Profile Av=0–1 mag in 0.005 steps and an additive magnitude normalization under conditionally independent reported JHK errors. These are central-parameter sensitivity cases, not a posterior or a complete propagation of stellar uncertainty. PHOENIX abundance mixture changes across its metallicity grid and may not match each star's measured alpha abundance.

W3 is excluded from fitting; compare in-band observed/predicted flux only after fit outputs are written. W1/W2 diagnostics are computed only if their separate band screens pass (six and nine stars respectively for the raw/Rv3.1 case). W4 is not fitted or scored. No band zero-point correction or dispersion is learned from these results.

| Rv=3.1 parameter case | N | Median W3 residual | MAD about median | Range |
|---|---:|---:|---:|---:|
| Raw GSP-Spec medians | 9 | +0.149% | 2.359% | −2.774 to +4.108% |
| Generic calibration sensitivity | 9 | +0.373% | 2.162% | −2.352 to +4.482% |

Across all 54 cases the range is −2.833 to +4.872%. None reaches the draft 20% excess floor in these conditional calculations. This is not a detection-limit or false-negative estimate. These nine candidates are not yet independently verified ordinary controls, and the sample is too small to calibrate distribution tails.

JHK chi-square spans 0.018–6.649. Source 2336863054027651456 has raw/Rv3.1 chi-square=6.464 and needs review; it is not removed based on the fit. Source 2759006524739613056 hits Av=0, indicating a boundary/weak-extinction issue. Noncontemporaneous variability, multiplicity, contamination, atmosphere discrepancy, stellar-parameter errors and zero-point covariance remain unresolved. Plot error bars show W3 measurement errors only, not predictive uncertainty.

## Verification and replay

**17 focused tests passed**, including eight new selection/calibration/reservation checks. These cover hash-order invariance, exposed-ID exclusion, duplicate rejection, selection independence from infrared magnitude, native exact-ID/duplicate-column preservation, published calibration polynomials and interior extrema, reserved-role protection and descriptive MAD calculation.

Native cohort replay verifies Gaia/IR response hashes, field schemas, statuses, IDs, frozen design, selection ranking/rows and calibration context. Both cohort and all development fit/comparison/summary outputs repeated byte-identically with socket connections blocked. Code/model hashes are preserved. Scientific plot inspected for legibility. Full repository CI is checked separately on the final branch commit; this report does not imply a live deployment.

The archive provides raw observations, native PHOENIX/filter/Vega replay inputs, full provenance, selection, outputs, code, tests and plot. From its echolens directory:

```
python -m pip install -r requirements-nir.txt
python -m pytest tests/test_calibration_cohort.py tests/test_calibration_development.py -q
python -m scripts.calibration_cohort replay
python -m scripts.calibration_development
python -m scripts.calibration_figures
```

Do not rerun selection over the frozen file or refresh data automatically. Historical sibling modules are included as imported numerical dependencies; their older experiment CLIs are outside this package's replay scope.

## Next gate

Review the nine development counterparts quantitatively in images and validate uncertainty propagation, stellar-parameter/calibration sensitivity and spectral-resolution adequacy. Specify the predictive error model and acceptance rules before using the reserved validation group. Validate performance on those reserved stars without retuning against their residuals; a failed validation requires a new declared development version and fresh validation data. Keep all failed/flagged cases and model changes in the audit trail.

PR #7 remains draft/unmerged. No control assignments or production registry inserts were made.

## Primary references

- [Gaia GSP-Spec calibration](https://www.cosmos.esa.int/web/gaia/dr3-gspspec-metallicity-logg-calibration), official native HTML archived with hash.
- [Gaia DR3 astrophysical parameters and flags](https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_astrophysical_parameter_tables/ssec_dm_astrophysical_parameters.html)
- [Gaia programmatic access](https://www.cosmos.esa.int/web/gaia-users/archive/programmatic-access)
- [AllWISE catalog fields](https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html)
- [2MASS PSC](https://irsa.ipac.caltech.edu/data/2MASS/docs/releases/allsky/doc/sec2_2a.html)
- [STScI PHOENIX](https://ssb.stsci.edu/cdbs/grid/phoenix/), [CALSPEC](https://ssb.stsci.edu/cdbs/calspec/), [SVO filters](https://svo2.cab.inta-csic.es/theory/fps/), [G23 extinction](https://dust-extinction.readthedocs.io/en/stable/api/dust_extinction.parameter_averages.G23.html)
