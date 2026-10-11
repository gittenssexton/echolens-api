# EchoLens Experiment 003H — 250-source epoch-window crossmatch triage

**2026-10-11 — completed offline analysis, NOT a certified crossmatch study.**

## Validated result

This analysis uses the **unchanged real LAMOST DR9 spectra and Gaia DR3 source records** from [Experiment 003](../experiment_003/REPORT.md) and [003G](../experiment_003/GAIA_AUDIT.md). The post-hoc engineering protocol was [committed first](../../docs/EXPERIMENT_003H.md), explicitly acknowledging the already-known 5.12-arcsec difference. This is **not** a blinded prospective analysis.

| Diagnostic | Result |
|---|---:|
| Original LAMOST/Gaia pairs | 250 |
| Pairs with Gaia proper motion and PM uncertainties to evaluate a linear bound | 247 |
| Missing adequate PM assessment | 3 |
| Pairs with original published coordinate offset >3 arcsec | 1 |
| Pairs whose original offset remains >3 arcsec **even subtracting the largest possible linear Gaia PM correction over the official DR9 observation period** | **1** |
| Independently certified astrometric counterparts | **0** |
| Real individual LAMOST `obsdate`/`mjd` obtained in this phase | **0** |

The remaining 246 PM-assessable pairs all require actual observation epoch/fiber-pointing verification too. Under the strict provenance gate, **no match is promoted to a certified source**.

### Leading flagged source

- LAMOST published spectrum `obsid=655310123`; published Gaia DR3 source ID `876451818359869824`.
- Gaia catalog reference epoch 2016.0, uncorrected separation 5.1201 arcsec (previous 003G diagnostic).
- Gaia DR3 proper motion `pmra=-6.576 mas/yr`, `pmdec=-24.698 mas/yr`, total **25.55846 mas/yr**.
- Given full official LAMOST DR9 observation period 2011-10-24 through 2021-06-30, longest possible elapsed time from Gaia 2016.0 is about **5.495 Julian years**. Largest possible linear PM shift is about **0.1404 arcsec**.
- Simple triangle-inequality lower bound on remaining angular difference: **4.9797 arcsec**. Proper motion alone during the DR9 period is insufficient to reconcile the 5.12-arcsec separation.

**Interpretation limit:** VizieR Huang+ `RAJ2000/DEJ2000` are published sky-coordinate values; they have not been established as the actual LAMOST **fiber-pointing coordinates at the observation date**. The analysis does **not** model precession between differing coordinate frames, positional systematics, LAMOST fiber offsets, parallax or nearby blending, and it does not substitute any invented observation date. The 4.98" bound is a **conditional diagnostic**, not proof of a wrong counterpart or evidence of technology. The large-offset source is a manual inspection priority.

## Reproducibility

[Successful GitHub Actions run 38147775558](https://github.com/gittenssexton/echolens-api/actions/runs/38147775558): **45 tests passed**; restored the exact original Experiment 003 and 003G frozen results, verified 250 paired identifiers, executed two local-independent standard-library replays, and confirmed byte-identical `results.json`. Zero native measurements, uncertainties, source IDs, science decisions, or Render settings were altered.

- [Durable archived Experiment 003H result ZIP in Echo Lens Drive](https://drive.google.com/file/d/1-H69obQRaZQwHaQTL6o5fJjv88mvrfZb/view?usp=drivesdk), verified as 10,426-byte ZIP.
- The corresponding GitHub Actions artifact expires 2026-11-10, but the exact data are archived in Drive.
- `scripts/lamost_epoch_003h.py` also contains a strict **optional** importer for an **official, user-authorized LAMOST DR9 v2 LRS General Catalog CSV** keyed by exact `obsid`, retaining original metadata, original byte SHA-256, observation date, MJD, `ra_obs`, `dec_obs`, `offsets` and `offsets_v`. No official CSV was supplied or fetched in this run.

## Next experimental gate

**Acquire actual observation metadata** for the 250 known `obsid` values from the official LAMOST DR9 v2.0 LRS General (or AFGK Parameter) catalog, using the [official documented fields](https://www.lamost.org/dr9/v2.0/doc/lr-data-production-description). The public site documents CSV/FITS catalog downloads, while the SQL query page redirects to login. Thus no undocumented anonymous API is assumed.

With dated fiber coordinates and fiber-offset information available, implement actual epoch-aware Gaia propagation with uncertainties and compare alternatives, including nearest Gaia neighboring objects and crowding. Do not assign stars to clean controls until those data and astrophysical characterization pass an independently registered quality criterion.

**No astrobiological, technosignature, or anomalous stellar light result is claimed.**


---

### Research update (2026-10-11; Experiment 006B, later evidence)

This report preserves its original observations and interpretation at the time. Subsequent exact-obsid archival retrieval from the public **ESA ESASky LAMOST DR9 LRS General** table shows that the highlighted `obsid=655310123` was **deliberately fiber-offset**: `offsets=1`, `offsets_v=4.89 arcsec`, observed fiber input-to-pointing separation **4.8853 arcsec**, observation date **2018-03-12 (MJD 58189)**. This directly accounts for the dominant part of the prior **5.1201 arcsec** Gaia-to-fiber offset and makes it **incorrect to continue treating that displacement as an unexplained stellar signal**. The original VizieR activity-table and ESA mirror fiber coordinates agree to recorded precision. ESA's Gaia ID for this record is `-9999` (missing), so a fully independently certified Gaia source association **still requires work**.

See the full **[Experiment 006B measured-data report](../experiment_006/RESULTS.md)** and archive. This update is an audit annotation, not a retroactive change of the older preregistered findings.
