# GALAH DR4 Reference 001 — integrity update (2026-10-12)

Status: **engineering verification, not an astronomical finding**. No anomaly or technosignature score.

## Correct reference object

The 2026-10-12 discussion provisionally used `sobject_id=140116004301057`, because it is the GALAH spectrum-viewer example. That number is **not yet qualified** as a clean FGK dwarf; it remains a demonstration target only.

The existing EchoLens 2026-10-11 acquisition audit already selected a **qualified** reference: Gaia DR3 `3064554891927687296`, GALAH `sobject_id=170416001901162`. Recorded catalogue values: Teff=5973.1294 K, logg=4.3823977, Gaia G=9.001117 mag; both mainstar and visit `flag_sp=0, flag_red=0`. Existing allspec analysis-spectrum FITS and SSA-converted spectra and hashes are archived in Drive. Do not redownload or replace their raw bytes merely to run this QA. See `ECHOLENS_GALAH_DR4_F01_HANDOFF_2026-10-11.md` and `README_FGK_AUDIT.md` in the Echo Lens Drive.

## Resolved GALAH fitting-mask polarity

The upstream pipeline saves `save_spectrum['mob'] = unmasked_opt` in `spectrum_analysis/galah_dr4_spectrum_analysis_single.py`. The `unmasked_opt` selection is explicitly computed from residual fit thresholds, masked synthesis regions, and vital spectral-line regions. Upstream `spectrum_post_processing/galah_dr4_post_processing.py` calculates `px_used_perc = 100 * count_nonzero(spectra['mob']) / len(spectra['mob'])`.

**Conclusion (upstream source-code evidence): `mob=True` means selected / unmasked for GALAH fitting; `mob=False` excluded from the fit.** This independently resolves the polarity left open in the earlier Claude review. It does **NOT** certify good detector pixels or document cosmic-ray rejection.

Source links:
- https://github.com/svenbuder/GALAH_DR4/blob/main/spectrum_analysis/galah_dr4_spectrum_analysis_single.py
- https://github.com/svenbuder/GALAH_DR4/blob/main/spectrum_post_processing/galah_dr4_post_processing.py

For the archived clean dwarf 14,285 of 15,090 Boolean entries were True and 805 False (as counted and recorded by the prior acquisition agent, **not remeasured during this update**).

## SSA arm-integrity gate

Drive review `REVIEW_GALAH_ONE_STAR_AUDIT_2026-10-11.md` documents Data Central `*_G.fits` files inconsistent with green-arm wavelengths: dwarf labelled G actually has `BAND=I`, WMIN=7584.87 A and the same DATASUM as the infrared file; a Ba visit labelled G actually has `BAND=B`, WMIN=4713.42 A.

Treat file naming / `FILT=G` arguments as requests, **never** proof of received arm identity. Quarantine the mismatched files for spectral residual analysis; preserve originals and hashes. The accepted green-arm wavelength range must be around 5649-5873 A. Do not blindly rename the wrong-spectrum bytes or invent the missing green observation.

Sources:
- Drive `REVIEW_GALAH_ONE_STAR_AUDIT_2026-10-11.md`
- https://www.galah-survey.org/dr4/the_spectra/
- https://academic.oup.com/mnras/article/551/3/stag1477/8751326

## Remaining blockers and immediate execution

1. Confirm all archived local input files by SHA-256 against their original manifest; inspect allspec `wave,sob,uob,smod,mob` using `True = used`. Compute **descriptive** masked and unmasked residual summaries only, with exposure provenance.
2. For each camera, validate `BAND`, wavelength axis / range, FITS provenance and number of HDUs. The 1-HDU Data Central SSA FITS is not the native 8-HDU GALAH reduction. Fail closed on missing / mislabeled G.
3. Identify the correct Data Central access/format route for true CCD2, verify WMIN near 5649 A. The published GALAH webpage's B/G/R/I template does not resolve the observed mismatch.
4. Obtain authoritative air-vs-vacuum wavelength declaration before line-position comparisons; until then do **not** match features to line lists or infer chemistry.
5. Native per-exposure reductions remain behind HTTP 403 in previous tests; permission is required, not a workaround. No claims about instrument cosmic-ray or bad-pixel flags until inspected.
6. Validate the 2026-10-12 example target `140116004301057` only as a separate candidate, never silently substitute it as reference 001.

No modifications to `main`, Render, frozen Gaia sample, or existing FITS. No scoring and no extraterrestrial-life inference.

## 2026-10-12 primary-source resolution — air wavelength calibration

The GALAH DR4 paper source states that ThXe arc calibration emission-line wavelengths are **reported in air**, the reduced spectra are interpolated onto that wavelength grid, and FITS `CRVAL1` / `CDELT1` describe that grid. GALAH DR4 analysis model spectra are subsequently interpolated onto the observed wavelength grid. Therefore treat the DR4 reduction / derived analysis spectra as **air-wavelength calibrated** unless individual file provenance explicitly demonstrates a further conversion. Conversion from vacuum laboratory lists is required for line matching; preserve the original convention separately from a converted copy.

Primary source: https://github.com/svenbuder/galah_dr4_paper/blob/main/galah_dr4_paper.tex (GALAH reduction paragraph beginning 'Wavelength calibrations are performed via Chebyshev...', near source line 2878 in GitHub rendering).

This resolves the prior 'air vs vacuum unknown' item **for DR4 reduction and derived analysis wavelength grids**. Do not assume unrelated Gaia, WISE, or external laboratory resources share the same convention.

## Actual archived QA and fail-closed engineering test

Re-analysed the frozen GALAH Reference 001 archive offline. All five stored FITS file hashes matched the archived SHA-256 manifest. Archive G-labeled SSA FITS wavelength WCS identifies IR, and the 4096 flux pixels match the distinct I-labelled file exactly. The separate original GALAH `single_fit_spectrum.fits` includes legitimate 5647.70–5871.63 Å model-analysis data. See Drive `GALAH_REF001_QC_2026-10-12/GALAH_REF001_SSA_ARM_INTEGRITY_V1.json`.

A new standalone offline gate, `scripts/galah_ssa_integrity.py`, inspects actual FITS headers and WCS, verifies the requested camera against the header, catches duplicate pixel payloads across cameras, records SHA-256 provenance and marks compromised products `quarantine=true` / `passed=false`. On the frozen archive B and R passed camera-integrity checks; G and I were blocked due to mislabeled/duplicate data. It emits exit code 2 on a failed audit, preventing downstream workflows from silently treating these as four independent camera spectra.

Five new unit tests use clearly labeled **synthetic test-only FITS fixtures** to validate parser and failure gates; these are NOT astronomical observations. Combined with five prior locally run tests, 10 bounded engineering tests passed on 2026-10-12. A hosted GitHub Actions test run was **not** invoked or verified in this update. No code was merged or deployed.

Further access issue: Data Central previously returned HTTP 403 for native eight-HDU reduced exposure files. Continue to request authorized access; do not treat the SSA single-HDU files as original reduction products. No chemical-line identification, scoring, or technosignature claim is authorized yet.
