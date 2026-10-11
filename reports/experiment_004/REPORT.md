# EchoLens Experiment 004 — Gaia DR3 neighborhood ambiguity pilot

**Executed:** 2026-10-11, Gaia DR3 real observations served through NASA/IPAC IRSA, **scientific status:** catalog-association triage only. This was a post-hoc, explicitly flagged 1-target investigation supplemented with 24 hash-selected targets; **not** a prospective astronomical detection test or representative control sample.

## Registered experiment and principal findings

The pre-acquisition protocol is [EXPERIMENT_004.md](../../docs/EXPERIMENT_004.md), frozen before any Gaia neighborhood retrieval. Input is the exact, already archived 250-spectrum Experiment 003 LAMOST activity dataset and 003G Gaia audit, with raw JSON SHA-256:
- LAMOST Experiment 003 result: `efc4f3eaf5f5e1df8b60aa1897ffd93d44c3b05fe69318b27d3769fddb342e51`.
- Gaia Experiment 003G result: `d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748`.

| Preregistered measure | Observed result |
| --- | ---: |
| Deliberately highlighted target from 003G/003H | 1 |
| Independently hash-selected other LAMOST targets | 24 |
| Unique sources actually retrieved in 25 original Gaia DR3 cones | **41** |
| Target cones where the original published Gaia ID is present | **25/25** |
| Target cones where published ID is nearest to LAMOST *catalog* coordinate | **25/25** |
| Cases with another Gaia source closer than published ID | **0** |
| Published ID absent from the 12" cone | **0** |
| Cones containing exactly 1 Gaia DR3 source | 13 |
| Cones containing exactly 2 Gaia DR3 sources | 8 |
| Cones containing exactly 3 Gaia DR3 sources | 4 |

There were 16 additional catalog sources across the 25 cones; all candidate rows, uncertainty fields, separation calculations, flags and response hashes remain in the archived results. The median nearest Gaia-source separation from the VizieR LAMOST published coordinate was **0.2027 arcseconds**, subject to unknown LAMOST observation epoch and source-coordinate meaning.

[View neighborhood count graph](https://drive.google.com/file/d/1WoAb1nR4dZq7hb1_JVZNRTAvgAQJpvEq/view?usp=drivesdk).

## Specific 5.1201-arcsecond investigation

- Published LAMOST `obsid=655310123`, `GaiaDR3=876451818359869824`.
- VizieR Huang+ table coordinate `RAJ2000=120.7483759°`, `DEJ2000=29.1898351°`.
- Gaia DR3 source `876451818359869824` lies **5.1201 arcseconds** from that coordinate, but it is the **only Gaia DR3 catalog object within the fixed 12-arcsecond cone**. No alternative Gaia source is closer in this retrieval.
- The published LAMOST activity table G magnitude and independent Gaia DR3 G differ by only **0.0003 mag** when rounded to 4 decimals. This is consistent photometric identification evidence, but it reuses Gaia-derived G in the LAMOST catalog and therefore **is not independent confirmation**.
- In earlier 003H calculations, linear Gaia proper motion alone can change the apparent offset by at most about **0.14 arcseconds** across the full LAMOST DR9 observing period, leaving 4.98 arcseconds under that limited model. The two reported catalogs do *not* necessarily use identical original observing-epoch fiber coordinates, and deliberate fiber offsets are not yet known.

**Interpretation:** The test **does not support a competing Gaia catalog neighbor** within 12" as an explanation of the 5.12" published-coordinate discrepancy. It does not prove the published source identity, establish instrumental causes, or identify anomalous electromagnetic behavior. Official DR9 v2.0 `obsid`-linked `obsdate/mjd`, `ra_obs`, `dec_obs`, `offsets`, `offsets_v` and original spectrum FITS header values are still required before any certified match.

## Original observations and reproducibility

- **25 real IRSA TAP VOTable responses**, one cone per frozen VizieR coordinate, 12" radius, all 17 requested original Gaia columns with uncertainties, source IDs as exact decimal strings.
- Preserve query and response metadata, request timestamps, TAP `QUERY_STATUS`, original bytes, checksums and field metadata. No error/OVERFLOW/duplicate was accepted.
- [GitHub Actions run 38150041783](https://github.com/gittenssexton/echolens-api/actions/runs/38150041783) succeeded: **52 tests passed**, one full retrieval, and a second offline replay with byte-for-byte identical derived `results.json`.
- [Permanent original observation and results ZIP in Echo Lens Google Drive](https://drive.google.com/file/d/1XS3o2aWUoigsIk2L5uNTQRKch_0A1lkA/view?usp=drivesdk), validated uploaded file size 129,748 bytes. The GitHub Actions mirror [artifact 11705912690](https://github.com/gittenssexton/echolens-api/actions/runs/38150041783/artifacts/11705912690) expires 2026-11-10.
- Stored separately on this **unmerged** branch; no Gaia 10k catalog replacement, source-row edits, anomaly scoring, WISE inference, `main` merge, or Render changes.

## Next scientific gate

The highest-value missing evidence is **authentic original LAMOST observing metadata** keyed to `obsid`, especially the flagged spectrum. The [official LAMOST DR9 v2 LRS General Catalog specification](https://www.lamost.org/dr9/v2.0/doc/lr-data-production-description) explicitly provides observation time and fiber offset fields. Its public SQL/FTP entry routes may require sign-in; no undocumented anonymous endpoint or fabricated observing date is acceptable. Use the existing strict `scripts/lamost_epoch_003h.py --official-csv` ingestion after retrieving an official CSV/FITS export; only then compare Gaia positions at the actual observation epoch and model fiber-pointing/offset uncertainty.

A scientifically useful next hypothesis test, **after crossmatch certification**, will ask whether a genuinely matched stellar cohort has statistically distinguishable electromagnetic residuals under astrophysical null models. This pilot cannot answer that question.
