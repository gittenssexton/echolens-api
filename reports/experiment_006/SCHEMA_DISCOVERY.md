# EchoLens Experiment 006A — ESA TAP catalog discovery result

**2026-10-11 — completed successfully.** Public schema discovery only; **zero** stellar observations queried in this stage. Protocol [EXPERIMENT_006.md](../../docs/EXPERIMENT_006.md) was committed before query execution.

## Authenticated-by-public-service observation metadata source discovered
The publicly accessible ESASky TAP `https://sky.esa.int/esasky-tap/tap/sync` returned four LAMOST metadata tables:

- `catalogues.mv_lamost_dr8_lrs_fdw`
- `catalogues.mv_lamost_dr8_mrs_fdw`
- **`catalogues.mv_lamost_dr9_lrs_fdw`**
- `catalogues.mv_lamost_dr9_mrs_fdw`

The DR9 **LRS General** table is unambiguous and has a typed 40-column schema, including:

| Field | ESA TAP datatype | Description / unit |
|---|---|---|
| obsid | int | Unique spectrum identifier |
| obsdate | char | Target observation date |
| mjd | int | Modified Julian day |
| lmjd | int | Local modified Julian day |
| ra, dec | double | Input target coordinates, degrees |
| ra_obs, dec_obs | double | Fiber pointing coordinates, degrees |
| offsets | short | Whether deliberate fiber offset applied |
| offsets_v | double | Fiber offset magnitude, arcseconds |
| gaia_source_id | char | Published Gaia DR3 crossmatch identifier |
| gaia_g_mean_mag | double | Gaia DR3 G, magnitudes |
| snri, snrz | double | Published signal-to-noise |

This is the complete field set needed to test our instrumental-offset explanation, *if exact sample obsids are represented in the ESA mirror*.

## Reproducibility
[Passing workflow run 38151942275](https://github.com/gittenssexton/echolens-api/actions/runs/38151942275): **61 automated tests passed**, original VOTable metadata responses for four schema tables preserved with SHA-256, query strings, retrieval UTC and typed units. [Permanent ESASky metadata archive in Echo Lens Drive](https://drive.google.com/file/d/1TvY3mBGM29yJbG_72Fc0zL5yyJSlIxed/view?usp=drivesdk) (12,026 bytes).

**Critical release caution:** ESA's ESASky catalog documentation reports 11,211,028 spectra for LAMOST DR9 LRS; LAMOST's official DR9 v2.0 description reports 10,809,336. We **cannot** claim release identity simply because both are called DR9. The follow-up Experiment 006B checks exact 250 `obsid` correspondences and per-source differences under a new frozen protocol.

This stage introduces **no** new astronomical result, no source match certification, no Render/main changes and no technosignature claim.
