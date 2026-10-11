# EchoLens Experiment 006B — 250-spectrum ESA LAMOST DR9 observation/fiber-offset verification

**Executed 2026-10-11; status: real-data instrumental hypothesis strongly supported for flagged spectrum, catalog crossmatch still not independently certified.** This is a *post-hoc* investigation of an already observed discrepancy, **not** a blinded anomaly search or technosignature detection.

## Registered source and reproducibility
- Exact post-schema registration: [EXPERIMENT_006B.md](../../docs/EXPERIMENT_006B.md), committed **before ESA spectrum data requests**.
- ESA public ESASky TAP, exact LRS table `catalogues.mv_lamost_dr9_lrs_fdw`, publicly documented 40 fields. Original ESA metadata source: [Experiment 006A](SCHEMA_DISCOVERY.md).
- Same frozen **250 genuine** original LAMOST/Huang+ DR9 `obsid` values and published Gaia DR3 observations (input JSON SHA-256 pinned in protocol).
- Exactly ten 25-obsid ADQL requests, original ESA **VOTable bytes and all field metadata** preserved with SHA-256, request, time and HTTP headers. **No replacement, filtering or rewriting** of the original two survey archives.
- [Passing research GitHub Actions run 38152809325](https://github.com/gittenssexton/echolens-api/actions/runs/38152809325): **68 tests passed**. Original first eight responses restored from earlier failure artifact rather than re-fetched, two further batches acquired, complete derived result reproduced byte-for-byte with no network.
- [Permanently archived native ESA data + all 250 derived source outcomes in Echo Lens Drive](https://drive.google.com/file/d/1GZcNqYW5CnIIGjFTr1DAva3-gUmzw2vg/view?usp=drivesdk), confirmed 78,165-byte ZIP.
- [Visualization of published offset flag and actual input-to-fiber separation](https://drive.google.com/file/d/1ZU9vL5mJzMac7pTVALDc09pGUG1M8iq3/view?usp=drivesdk).

## Complete study outcomes

| Exact registered measure | Observed |
| --- | ---: |
| Requested original LAMOST spectrum obsids | **250** |
| Found in ESA LAMOST DR9 LRS mirror by exact obsid | **241** |
| Missing in this ESA mirror (not substituted) | **9** |
| Published Gaia DR3 ID agreeing with original LAMOST/VizieR | **238** |
| Valid but different ESA Gaia IDs | **2** |
| ESA Gaia ID sentinel, absent or malformed | **1** |
| ESA fiber deliberate-offset flag true | **9** |
| ESA fiber offset flag false | **232** |
| Date vs MJD discrepancies over 2 days | **0** |
| Independently certified Gaia–LAMOST astrophysical counterparts | **0** |

All nine `offsets=true` source records report an offset distance `offsets_v` agreeing with the independently calculated `ra,dec` input-to-`ra_obs,dec_obs` fiber displacement within **0.0047 arcseconds** (maximum absolute difference), indicating consistent data columns and rounding. Two catalog Gaia ID disagreements are preserved (LAMOST obsids `235608062` and `844313076`) and require per-source assessment; neither is silently repaired.

**Unresolved ESA mirror observations:** `52606232`, `257813193`, `318809041`, `447016213`, `458106245`, `459815059`, `475114198`, `570209101`, `574314070`. Their original spectra stay in the registry and should not be assumed false or unusable solely due to mirror coverage.

## Highlighted source — direct documented instrumental finding

**Original published LAMOST spectrum `obsid=655310123`**, original Huang+ published Gaia DR3 `876451818359869824`, apparent G≈9.451.

| ESA public archived DR9 LRS original field | Original value |
| --- | --- |
| `obsdate` | **2018-03-12** |
| `mjd` | **58189** |
| `offsets` | **1 / true** |
| `offsets_v` | **4.89 arcsec** |
| `ra,dec` original input catalog | 120.74687444°, +29.18948389° |
| `ra_obs,dec_obs` actual published fiber point | 120.74837590°, +29.18983510° |
| Input-to-fiber angular displacement | **4.8853 arcsec** |
| Original VizieR/Huang+ fiber-coordinate vs ESA fiber coordinate | **0.0000 arcsec**, at archived precision |
| Original Gaia DR3 2016.0 position vs ESA fiber | **5.1201 arcsec**, uncorrected for observing epoch |
| ESA Gaia `gaia_source_id` | **-9999**, an invalid/missing identifier sentinel |
| ESA `gaia_g_mean_mag` | **-9999**, also sentinel, NOT a physical measurement |

**Scientific resolution:** The large recorded offset is explained **predominantly by an explicitly documented deliberate LAMOST fiber-offset operation**. The 4.89" published offset agrees with coordinate geometry to about 0.0047". It is therefore inappropriate to present the 5.12" offset as an unexplained stellar observation or a technosignature lead. The residual difference is not itself a new anomaly.

The ESA copy's missing `gaia_source_id` prevents claiming that the specific optical-spectrum-to-Gaia identifier was independently validated by ESA; the later Huang+ activity catalog supplies an ID and Gaia itself contains that star. Catalog releases and crossmatch pipelines differ. The ESA LRS survey and the Huang+ table share *identical fiber sky positions* for this exact obsid, but full source-identity certification remains a separate astrometric/modeling task.

### Optional properly labeled linear PM diagnostic (not a full astrometric propagation)
From archived Gaia DR3 `ra=120.74683645005°`, `dec=29.18936968555°`, `pmra=-6.576`, `pmdec=-24.698` mas/year, the Gaia 2016.0 input-target separation is about **0.428 arcsec**. Simple tangent-plane Gaia proper-motion propagation over `(58189−57388.5)/365.25 ≈2.192` Julian years gives **approximately 0.484 arcsec** between the propagated Gaia direction and original LAMOST input coordinates; about **5.152 arcsec** from propagated Gaia to the published fiber. These **approximate diagnostics omit full covariance/parallax/perspective motion/pointing uncertainty** and do not certify the Gaia match. They are consistent with a large deliberate `4.89"` fiber displacement plus ordinary catalog-position differences. Epoch-correct source assignment remains unresolved.

## Provenance and version warning
The ESA table is publicly called **LAMOST DR9**, but ESA describes 11,211,028 LRS spectra while official LAMOST DR9 v2.0 describes 10,809,336. Matching a specific obsid/date/position is evidence of record concordance, not proof of full release equivalence. Do not rename source to official LAMOST DR9 v2.0 until original DR9-v2 FITS/catalog header or official export is obtained.

Related source documentation:
- ESA: https://www.cosmos.esa.int/web/esdc/esasky-catalogues
- LAMOST: https://www.lamost.org/dr9/v2.0/doc/lr-data-production-description

## Immediate next scientific gate
1. **Correct the earlier Experiment 003H/004/005 interpretation:** flag `obsid=655310123` as explained by published instrumental offset, *not* outstanding mystery; preserve original analyses and report why the explanation changed.
2. Examine **two conflicting Gaia ID values**, **one missing ESA ID**, and **nine sources absent in ESA mirror**, while retaining all original spectroscopic observations and their uncertainties.
3. Register a new cohort-matching analysis that excludes/calibrates fiber-offset spectra for spatial association tests, and requires uniform spectral-quality/astrometric flags.
4. If warranted, retrieve original official LAMOST DR9 v2 FITS header `OFFSET`, `OFFSET_V`, `DATE-OBS` for one independent authority check. No new ranking, technosignature probability or Render change.

**No changes** to deployed Render, production registry, source measurements, branch `main` or older historical results.
