# SP01-P2B transport amendment — original GALAH DR4 unavailable through tested public services

2026-10-12, recorded **before any exploratory sample ranks or spectrum-residual evaluation**.

## Exact observed failure, not silently corrected
- GitHub Actions run 38283090813: independent VizieR Escorza+2026 original CSV acquisition **succeeded** (1059 real Gaia DR3 identifiers, original 21,164-byte response retained); subsequently public Data Central TAP request failed HTTP 400.
- Run 38283465773: even a minimal `SELECT TOP 1 gaiadr3_source_id,sobject_id FROM galah_dr4.main_star WHERE flag_sp=0` returned an IVOA error explicitly identifying the `galah_dr4.main_star` table as **unknown in that TAP service**. Data Central's newer `/api/services/query/` REST POST returned HTTP 403 from the GitHub runner. Neither error indicates a stellar population or physics result. Both HTTP responses and query text were preserved in the run artifact.
- Official Data Central documentation indicates that older TAP has limited tables and suggests its query service instead. No attempt to bypass the HTTP 403 will be made.

## Alternate feasibility source (NOT scientific source-equivalent)
- Catalogue: Kos et al. (2025), VizieR `J/A+A/703/A104/catalog`, a **detrended** 917588-row GALAH DR4-derived table. It is not the native original GALAH DR4 `allstar` FITS/`main_star` table. This distinction is attached to every output; source-specific validation required before interpreting apparent outliers.
- Independent positives: Escorza et al. (2026), VizieR `J/A+A/712/A111/catalog`, 1059 s-process-rich GALAH sources, original IDs preserved.
- No changes to the SP01-P2B Teff/logg/[Fe/H]/SNR or flag thresholds, source-ID hash, calibration/holdout split, or prior-exposure exclusion. All queries are bounded, raw responses and SHA-256 recorded, and no star spectra downloaded.
- Any generated result is a **provisional 50-star VizieR-derived FEASIBILITY manifest**, NOT the predeclared original-catalogue confirmatory 50-star cohort. We will validate a sample of source fields against native GALAH or an authorized Data Central service before scientific interpretations.
- If any published field is missing, source identifiers are not exact, or any stratum cannot supply 10 sources, the feasibility cohort remains blocked and failure is logged. Negative outcomes will not be replaced with fabricated stars.

Sources: https://www.galah-survey.org/dr4/the_catalogues/ ; https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=J%2FA%2BA%2F703%2FA104 ; https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=J%2FA%2BA%2F712%2FA111 .
