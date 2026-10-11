# EchoLens Experiment 005 — bright-star fiber-offset hypothesis (real-data result)

**Executed 2026-10-11. Status: exploratory post-hoc instrument/crossmatch investigation; the actual official fiber OFFSET flag is NOT known.** Target and hypothesis were chosen after seeing Experiment 003G's flagged 5.1201" separation. This is not an independent or blinded astronomical discovery.

## Evidence and public scientific sources

LAMOST DR9 v2.0 documents deliberate fiber pointing displacements for a fraction of **luminous stars to avoid detector saturation**, and its LRS General/Input catalogs supply `obsid`, `obsdate/mjd`, `ra_obs`, `dec_obs`, `offsets` and `offsets_v`. FITS primary headers can record `OFFSET`, `OFFSET_V` and `DATE-OBS`. Huang et al. 2024 VizieR `J/ApJS/272/6/catalog` describes its published `RAJ2000/DEJ2000` as the position of the *fiber point (J2000)*, not necessarily the same sky position as Gaia's stellar position at epoch 2016.0. We **still lack the actual LAMOST observation date and offset flags for these exact spectra**.

- Official science and catalog field documentation: https://www.lamost.org/dr9/v2.0/doc/lr-data-production-description
- LAMOST public catalog page: https://www.lamost.org/dr9/v2.0/catalogue
- Huang et al. 2024 source ReadMe: https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/J/ApJS/272/6?format=html&tex=true

## Frozen authentic observations and analysis

- 250 published **real LAMOST DR9 spectra** from original Experiment 003, original `results.json` SHA-256 `efc4f3eaf5f5e1df8b60aa1897ffd93d44c3b05fe69318b27d3769fddb342e51`.
- Same 250 exact Gaia DR3 IDs and archived astrometry from Experiment 003G, original `results.json` SHA-256 `d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748`.
- All 250 original spectra retained, with G magnitudes, observational positions, exact obsid/Gaia ID mapping and a *catalog-coordinate, epoch-unqualified* angular separation.
- No source substitutions, invented dates, new astrometric catalog requests or astrophysical candidate rankings.

### Descriptive comparisons

| G brightness partition | Number of spectra | Median Gaia–LAMOST coordinate separation | >1" | >3" |
| --- | ---: | ---: | ---: | ---: |
| G below 10 | 1 | 5.1201" | 1 | 1 |
| G 10 or fainter | 249 | 0.2129" | 10 | 0 |
| **G below 11** | **10** | **1.28515"** | **6** | **1** |
| **G 11 or fainter** | **240** | **0.20895"** | **5** | **0** |

Spearman rank correlation between apparent G magnitude (larger means *fainter*) and epoch-unqualified angular separation across 250: **rho = −0.3471456**. This is a descriptive sample correlation, **not an instrumental offset probability or prespecified astrophysical significance test**. The bright cutoff is a convenience for exploratory characterization, not a calibration of when LAMOST activates offsets. Other instrumental, coordinate transformation, calibration or catalog artifacts may also contribute.

**Flagged source:** LAMOST spectrum `obsid=655310123`, published Gaia DR3 `source_id=876451818359869824`, G≈9.45133, original fiber-coordinate-vs-Gaia separation **5.1201"**. It is both **brightest (rank 1/250)** and **largest position discrepancy (rank 1/250)**. The nine *other* stars with G<11 still have median raw separation ≈**1.2791"**, meaning the bright-subsample trend is not produced solely by the highlighted object. This strengthens the rationale for checking the official instrument offsets, but does NOT establish that offsets actually occurred.

[View archived original-observation scatterplot](https://drive.google.com/file/d/1x_Z9TN6vO6Iqgoa7hm8NIYSjC4_Y-HL0/view?usp=drivesdk).

## Reproducibility and access check

- [GitHub Actions run 38151214156](https://github.com/gittenssexton/echolens-api/actions/runs/38151214156): **57 automated tests passed**, original immutable source artifacts verified by SHA-256, derived JSON generated twice and compared byte-for-byte.
- Public official page GET `https://www.lamost.org/dr9/v2.0/catalogue` succeeded (HTTP 200, HTML SHA-256 `705a99e92ef6862e13202aef67621d491474f84eb6def3b4ec44166d365b1cb9`). **No direct publicly rendered CSV/FITS download links** in the static HTML. The public SQL and FTP links route to login. The access check obtained **zero original LAMOST DR9 individual MJD/offset records**. Do not treat this as proof the catalog is unavailable via its interactive authenticated interface.
- Full derived JSON and official public-site access check permanently archived in [Echo Lens Google Drive](https://drive.google.com/file/d/1_qUrRB62hacH4oornb8dlbgqAw8qrPS9/view?usp=drivesdk), verified 14,186-byte ZIP; GitHub Actions transient mirror expires 2026-11-10.
- No changes to existing original observations, `main`, Render, serving SQLite or source interpretations.

## Next evidence gate

Retrieve an **authenticated official LAMOST DR9 v2 LRS General/Input CSV or FITS** export for the exact 250 `obsid` identifiers, particularly `655310123`, or obtain its original LAMOST spectrum FITS header. Inspect `obsdate/mjd`, `ra_obs/dec_obs`, `offsets`, `offsets_v` and source-reported fiber targeting and position errors, with original download/byte SHA-256 provenance. The pre-existing strict `scripts/lamost_epoch_003h.py --official-csv` reader can ingest an authorized export after documented column/type checks. Independently propagate Gaia to the actual observation epoch and incorporate astrometric errors. If `offsets` is true and the published value plausibly agrees with the measured coordinate discrepancy, then mark the deliberate instrumental explanation as supported, not beforehand.

Until those official records exist, **0/250 are verified for this instrument-offset hypothesis**. The current evidence is suggestive of a common observing procedure, not extraterrestrial electromagnetic behavior.
