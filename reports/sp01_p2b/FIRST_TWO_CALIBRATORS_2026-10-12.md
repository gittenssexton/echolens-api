# EchoLens SP01–P2B: first two frozen calibration stars — real GALAH DR4 spectra

**Date:** 2026-10-12. **Status:** bounded acquisition and engineering diagnostic completed, **not** scientific discovery. No source-level calibration or technosignature candidate claims.

## Frozen selection and source provenance
Two source IDs were chosen as the first two **calibration** entries in the independent 50-star **provisional Kos et al. 2025 detrended GALAH DR4/VizieR** selection. Neither source has been independently qualified against the *original* GALAH allstar source catalog. The full source manifest was not modified, and the 20 holdout sources were not read by the analysis code.

- Full manifest SHA-256: `ef62ec0bd5afd79a8c39613f2796943937dd09d9eb6e6bfabe644522e2beed32`.
- Star A: Gaia DR3 `39909218369012608`, GALAH `sobject_id=151111003101245`, detrended `Teff=5100.66 K`, `logg=4.535772`, `flag_sp=0`, `flag_red=0`.
- Star B: Gaia DR3 `4616578742686592`, GALAH `sobject_id=221003001101138`, detrended `Teff=5545.56 K`, `logg=4.461501`, `flag_sp=0`, `flag_red=0`.

## Actual observation bytes and verification

Using a new, bounded read-only GitHub Actions workflow, retrieved **two real GALAH DR4 single-fit analysis spectra** from the official AAO Data Central cloud archive under `analysis_products_single/YYMMDD/sobject_id/`.

| Star | Original analysis FITS bytes | SHA-256 | Measured spectral pixels | Coverage |
|---|---:|---|---:|---|
| A | 506,880 | `0a60a1c555a2fbf941cf4e920f72db0581dcd31fe80440f7a31daf3c8acb3ff4` | 15,104 | B,G,R,I |
| B | 504,000 | `c2ae5820157b3c59a553375387aa1c14891ef112209bb9a35db8c6709ff5376e` | 15,096 | B,G,R,I |

BOTH files were re-read independently from the workflow artifact and validated as FITS primary HDU plus binary table `wave,sob,uob,smod,mob`, real flux, real uncertainty, and the selection Boolean mask; not fake or simulated spectra. The file names/URL use frozen exact `sobject_id`s; no independent original-GALAH main-source row proof has yet been collected. Raw source bytes preserved unchanged, hashes recorded.

## Bounded numerical result: model-fit QA, not discoveries

Compute `z=(sob-smod)/uob`, where `smod` was **fitted to these same measurements**; `uob` is the catalogue's formal pixel uncertainty; and GALAH `mob=True` is the model fit-inclusion mask (`mob=unmasked_opt` in upstream GALAH DR4 source). These z values **are not Gaussian discovery significances**. Adjacent residuals and errors are correlated, and fit masking is itself a function of observed-vs-model discrepancies.

**Red HERMES arm** (each has 4,096 pixels):

| Measurement | Star A | Star B |
|---|---:|---:|
| Pixels retained by fit | 3,958 | 3,953 |
| Retained pixels with \|z\| > 5 | 0.0505% | 0.0253% |
| Excluded pixels | 138 | 143 |
| Excluded pixels with \|z\| > 5 | 26.81% | 24.48% |
| Lag-1 adjacent correlation among fit-retained z pixels | 0.527 | 0.554 |

This is a caution about mask-conditioned comparisons, **not** an indication that the control stars are physically anomalous or that the masked portions are bad CCD pixels. No line-identification decisions, FDR/q-values, signal injections, source-level false-alarm estimates, or instrumental LSF corrections have been performed in this P2B micro-pilot.

## Retrieval limitations / erratum

The expected official eight-HDU native CCD1 reduction path yielded HTTP **404** for both visits. A 404 at the constructed path does **not** prove the spectra are physically absent or inaccessible via every supported archive interface. Preliminary SSA returned a green-labelled payload with `BAND=I` again; green SSA must be quarantined pending wavelength + hash check. A first-run parsing defect treated the FITS `BAND='B       '` card as a band mismatch because fixed-width quoted strings contain padding. After fixing the parser (`strip()`), an independently executed second run **confirmed a genuine SSA anomaly**: for both visits, the files requested with `FILT=B` have `BAND=B` but **red-band wavelength midpoint ~6761 Å**, and the files requested with `FILT=G` have `BAND=I`. The SSA B/G products are therefore **quarantined**, not treated as blue/green; no bytes were relabeled or reused. The second run [#5](https://github.com/gittenssexton/echolens-api/actions/runs/38285584220) passed 9 offline tests and repeated the 2 successful original allspec downloads. SSA single-HDU transformed files are not original eight-HDU reductions, even if their wavelength/arm labels pass.

## Science readiness / next gate

- Retrieve original GALAH DR4 allstar/allspec source rows for exact ID and quality confirmation, separate from the Kos detrended catalogue.
- Obtain native per-camera reduction including pixel-dependent `resolution_profile`, detector quality provenance, instrumental/telluric sky effects; do not transfer an LSF from an unrelated star.
- Freeze model and mask handling using only calibration stars; do not inspect source-disjoint holdout before preregistration of false-alarm threshold.
- Review any spectral pattern against normal atomic/molecular/telluric/instrument models. There are **zero** defensible technosignature detections in this experiment.

No changes to production API, main, Render or original archiving files. Full workflow archive, original FITS, script, tests and figures are retained with source SHA-256 and acquisition report.

**Authoritative methods:** https://www.galah-survey.org/dr4/the_spectra/ ; https://www.cambridge.org/core/journals/publications-of-the-astronomical-society-of-australia/article/galah-survey-data-release-4/06C38A8EA0FD888873BEA3C428DF4B50 ; upstream GALAH DR4 fitting source https://github.com/svenbuder/GALAH_DR4/blob/main/spectrum_analysis/galah_dr4_spectrum_analysis_single.py
