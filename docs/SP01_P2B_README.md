# EchoLens SP01-P2B: prospective 50-star control cohort

Prepared October 12, 2026. **Engineering-only / no cohort selected / no discovery claims.**

Why: The three-visit, two-star P2A scan found strong correlation and fit-mask censoring. P2B freezes a 40 ordinary + 10 separately published peculiar source-level cohort, *before* viewing any new red-window residuals. The 40 ordinary are split 20 calibration and 20 never-examined holdout. This pilot is too small to establish rare false-alarm probabilities.

## Run after acquiring real metadata

Create an input `galah_catalog.csv` from a specific SHA-256 archived GALAH DR4 **allstar/allspec** catalogue; export Gaia IDs from integer columns as exact decimal strings, not floating point. Required fields:

`gaiadr3_source_id,sobject_id,teff,logg,fe_h,snr_px_ccd2,snr_px_ccd3,flag_sp,flag_red,phot_g_mean_mag,bp_rp,ruwe`

Prepare **separate** `independent_positive_labels.csv` from *cited published classifications*, columns:

`gaiadr3_source_id,classification,reference_url`

Do not derive these labels from P2A residuals; catalogue-to-Gaia match and literature evidence must be independently checked. Both files are inputs, not claims that real stars have already been selected.

```
python -m scripts.sp01_p2b_select \
  --catalog-csv galah_catalog.csv \
  --positive-csv independent_positive_labels.csv \
  --raw-source-sha256 <64hex-digest-of-original-catalogue-FITS-or-response> \
  --catalog-source 'GALAH DR4 allstar 240705; source URI; query / extraction revision' \
  --manifest-json manifest.json \
  --manifest-csv manifest.csv
```

Runs offline, reads metadata only, SHA-ranks source IDs deterministically, checks four ordinary Teff/SNR strata and 10 published positives, excludes three prior development-exposed Gaia IDs, and exits with status 2 when any bucket is too small. The selection is not adaptive to anomaly results. A complete manifest is impossible without sufficient **real** catalog and independently referenced positive records. Preserve input native bytes, acquisition time and upstream checksums in Drive.

Synthetic-fixture engineering tests (NOT astronomical records):

```
python -m unittest discover -s tests -v
```

**Important:** `flag_sp==0` in the ordinary cohort selects well-fitted sources, which conditions the null and can systematically exclude unusual mismatches. A later population-wide scan must include flag-sensitive strata. `mob=True` reports pixels retained for GALAH's in-sample model fitting and is not a native detector pixel-quality mask. The script alone does not calibrate any significance, fetch spectra, or select aliens.

Protocol (updated for newly inspected user-uploaded native 8-HDU blue-camera engineering file): `docs/SP01_P2B_PROTOCOL.md`. Earlier work: https://github.com/gittenssexton/echolens-api/pull/28
