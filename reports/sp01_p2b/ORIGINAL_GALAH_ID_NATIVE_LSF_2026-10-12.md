# EchoLens SP01-P2B — Original GALAH Identity & Native LSF Audit
**12 October 2026.** Identity check: **PASS 2/2**. Native-camera LSF recovery: **BLOCKED 0/8**. Scientific discovery claims: **none**.

## Original independent catalogue confirmation
The original **Buder et al. (2025) GALAH DR4 all-spectrum catalogue**, mirrored by CDS/VizieR as `J/other/PASA/42.51/allspec`, provides independent original-release evidence for the two exact previously selected Gaia DR3 ↔ GALAH observation pairs. Both rows matched. This check is independent of the **Kos et al. (2025) detrended** GALAH data used to select our provisional sample.

| Measurement | Calibration star 1 | Calibration star 2 |
|---|---:|---:|
| Gaia DR3 source ID | 39909218369012608 | 4616578742686592 |
| GALAH sobject_id | 151111003101245 | 221003001101138 |
| Original flagSp | 0 | 0 |
| Original flagSpFit | 0 | 0 |
| Original flagRed | 0 | 0 |
| Original Teff K | 5051.4 | 5529.9 |
| Detrended Teff K | 5100.66 | 5545.56 |
| Original logg | 4.5313 | 4.4726 |
| Detrended logg | 4.535772 | 4.461501 |
| Original SNR CCD2 | 38.79 | 43.54 |
| Original SNR CCD3 | 56.97 | 55.36 |

Original-release source flags `flagSp=0`, `flagSpFit=0`, and `flagRed=0` for **both** visits; this is quality screening, not an independent certification of astrophysical normality. The original catalogue gives Teff 5051.43 K vs detrended 5100.66 K for star 1, and 5529.89 K vs detrended 5545.56 K for star 2. Treat these as differing published pipeline estimates, not temporal changes or anomalies.

## Reproducible source evidence
Original TAP request (full literal query):
```sql
SELECT TOP 4 "GALAH","GaiaDR3","flagSp","flagSpFit","flagRed","SNRpxCCD2","SNRpxCCD3","Teff","logg","RAJ2000","DEJ2000" FROM "J/other/PASA/42.51/allspec" WHERE "GALAH" IN (151111003101245,221003001101138)
```

Original TAP HTTP **200**; SHA-256 of returned CSV bytes: `8d11ccb0eae99fa64d69202fbb6551478cfc6321c5c1d9103567b06b3cec195f`.
Provider-native response saved as `original_galah_dr4_allspec_two_rows.native`, decoded row comparisons and camera probes recorded in `status.json`.
Official original catalogue: https://vizier.cfa.harvard.edu/viz-bin/VizieR-3?-source=J/other/PASA/42.51

## Actual LSF retrieval: unavailable
GALAH native 1D camera reductions include eight HDUs and a **resolution_profile** extension (HDU index 7) giving measured wavelength-dependent LSF FWHM. We made eight bounded requests to the published original-cloud paths (`observations/<date>/spectra/com/<visit><camera>.fits`, four cameras × two visits). **All eight returned HTTP 404**, with the original error-response byte length and SHA stored in `status.json`.
No camera FITS/LSF was downloaded for these two visits. The independently archived CCD1 spectrum for a *different* GALAH star cannot provide their instrumental resolution, and the mislabeled Data Central SSA exports from an earlier test cannot be used as a surrogate. Archive 404 does not prove no spectra exist; it documents the failure of these URLs at this time.

## Decision and next action
**GO:** two catalogue identities and original-release spectroscopic quality flags are now checked. **NO-GO:** visit-specific LSF validation, calibration of stellar-line significance or held-out anomaly search. Obtain authorized native eight-HDU camera files or the correct verified original archive route from the GALAH/Data Central maintainers. Preserve bytes, checksums, source IDs, native HDU7, associated sky/telluric corrections, uncertainties and failures. Until then use only descriptive analysis-spectrum or explicitly labeled assumed-LSF sensitivity tests.
Only these two development calibration stars were queried. The 20 holdout stars, `main` and Render were untouched.

