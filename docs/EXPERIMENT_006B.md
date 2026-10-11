# Experiment 006B — ESASky DR9 LRS date/fiber-offset retrieval (frozen pre-data)

**2026-10-11. Source discovered in 006A, no source rows retrieved yet.** This is an explicitly *post-hoc instrumental hypothesis follow-up* to the previously seen LAMOST `obsid=655310123`, Gaia DR3 `876451818359869824`, and ~5.1201 arcsecond coordinate difference. No statistical discovery, blinded hypothesis or astrophysical anomaly is claimed.

## Observational source
The public ESA ESASky TAP at `https://sky.esa.int/esasky-tap/tap/sync` exposed **one unambiguous** LAMOST DR9 **low-resolution General Catalog** table in the 006A schema:
`catalogues.mv_lamost_dr9_lrs_fdw`. Its metadata includes exact `obsid`, `obsdate`, `mjd`, original input `ra`, `dec`, actual fiber `ra_obs`, `dec_obs`, `offsets` (short integer), `offsets_v` (arcsec) and `gaia_source_id` (CHAR).
Original ESA metadata is captured in run 38151942275, artifact 11705674994, with raw VOTables and field units.

**Release-equivalence caution:** ESA describes 11,211,028 LRS spectra for its LAMOST DR9 table, versus 10,809,336 in original LAMOST DR9 v2.0 documentation. The ESA copy is *not automatically the same version*; preserve the ESA table designation in every output. A row-specific obsid and crossmatch match, plus identical coordinates and magnitude where possible, strengthens correspondence but does not resolve all release-version differences.

## Fixed exact sample and acquisition
Use the previous **unchanged** Experiment 003 250 spectra and Experiment 003G 250 Gaia source IDs, with source checksums:
`efc4f3eaf5f5e1df8b60aa1897ffd93d44c3b05fe69318b27d3769fddb342e51` and `d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748`.
All 250 exact `obsid` integers, one query per batch of **25**, sorted ascending, *including* priority obsid 655310123. No source substitution, fallback object or dropping missing IDs.

ADQL for each batch: `SELECT TOP 100 obsid,obsdate,mjd,ra,dec,ra_obs,dec_obs,offsets,offsets_v,gaia_source_id,gaia_g_mean_mag,designation,snri,snrz FROM catalogues.mv_lamost_dr9_lrs_fdw WHERE obsid IN (<batch>) ORDER BY obsid ASC`. `MAXREC=101`, server 100-row query ceiling above 25. Missing IDs are recorded; extra/duplicated/unrequested IDs and invalid TAP status cause failure. Each raw response is preserved as an unmodified byte SHA-256 with query, URL, UTC retrieval, HTTP metadata, original schema/units. Replays use only these frozen bytes. If ESA public query times out or refuses access, record failure without fabricating rows.

## Declared outputs
- Exact 250 expected obsid resolution rate, original published Gaia ID concordance vs the ESASky row, missing/duplicate/changed IDs, missing date/MJD/coordinates/flags, and potential date inconsistency. Do not silently coerce failed source links.
- For published fibers, actual `offsets` flag, published `offsets_v` in arcseconds, angular distance from `ra,dec` input target coordinates to `ra_obs,dec_obs` fiber coords, distance from original VizieR `RAJ2000/DEJ2000` to ESASky `ra_obs/dec_obs`, and *epoch-unqualified* separation from Gaia 2016. Flag discrepancies rather than forcing agreement.
- A separately labeled **linear proper-motion approximation** from Gaia DR3 ref epoch J2016.0 to ESA MJD, for diagnostics only. Use exact pmra as mu_alpha* (includes cos(dec)) and pmdec, keep source errors; do NOT call it full 6D or covariance-qualified propagation, do NOT certify astrometric counterpart.
- For the previously highlighted `655310123`, report exact published ESA `obsdate,mjd,offsets,offsets_v`, original observed fiber coordinate, independent Gaia identifier agreement and the observed geometry. The hypothesis of deliberate instrumental displacement is **supported** if the ESA-published `offsets` flag is true and the measured displacement is compatible with `offsets_v` within declared coordinate rounding; otherwise report lack of support or missing evidence, not technology.
- Preserve all failures and all 250 records. No control-star classification or technosignature inference.
- Two offline identical `results.json` replays required after acquisition.

## Distinguish what is NOT established
The ESA mirror is LAMOST-derived survey data, not independent observation. Per-source official LAMOST DR9 v2 original catalog/FITS remains gold standard for source-specific offset/crossmatch certification. Uncertainty/covariance, crowded neighbors, fiber placement and instrumental calibration still matter. No `main` or Render changes.
