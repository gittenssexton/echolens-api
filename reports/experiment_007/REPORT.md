# EchoLens Experiment 007 — full cross-catalog source-ID and DR8-coverage reconciliation

**Executed:** 2026-10-11. **Research type:** post-hoc source-provenance / observational archive validation only. Not a technosignature search or a test of hypothetical alien electromagnetic signals.

## Frozen basis and methods

Protocol [EXPERIMENT_007.md](../../docs/EXPERIMENT_007.md) committed before external source queries. Two previously observed ESA DR9 LRS vs published Huang+ (2024) Gaia identifier disagreements and all nine observations absent in ESA DR9 were **not reselected** after any outcome.

Inputs: unmodified real LAMOST DR9 Experiment 003, Gaia DR3 003G, ESA LAMOST DR9 LRS mirror 006B frozen results; original 006B result SHA-256 `73b2dbf80ff591d42386c4149dcea1e0ca2225569728dd94c8efacb7609b4fa7`, original Gaia audit 003G SHA-256 `d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748`.

New source archive requests: one **exact 4-ID Gaia DR3** IRSA TAP query, one **exact 9-obsid ESA LAMOST DR8 LRS** TAP query. Original unmodified VOTable XML, field metadata, uncertainties, query, HTTP info, UTC and SHA-256 retained; all ID and TAP status checks performed.

## Primary results

| Predeclared measure | Observed |
| --- | ---: |
| Disputed LAMOST spectrum obsids | 2 |
| Distinct Gaia DR3 source IDs requested | 4 |
| **Real Gaia DR3 IDs found** | **4/4** |
| Prior ESA DR9 missing spectrum obsids | 9 |
| **Same 9 obsids found by exact ID in ESA DR8 LRS** | **9/9** |
| Gaia source IDs in the 9 DR8 rows agreeing with the original Huang+ Gaia IDs | **9/9** |
| DR8 rows with deliberate fiber-offset flag | **0/9** |
| Gaia–LAMOST astrophysical source identities newly certified in this audit | **0** |

**Interpretation:** The missing nine observations are present in the historical ESA DR8 LRS catalog and share the previously published Gaia source IDs; their absence from the ESA DR9 mirror is clearly a **catalog-release/coverage mismatch**, not evidence that spectra did not exist. Never silently substitute DR8 into the DR9 source table. The 9 genuine observations and provenance remain preserved in their original experimental snapshot.

### Exactly conflicting Gaia DR3 source associations

All four candidate IDs exist in Gaia DR3. The observed (previously frozen) ESA DR9 `obsid`, `mjd`, input and fiber sky positions were compared against newly retrieved original Gaia astrometric coordinates and G band photometry. The tabulated angular separations are **diagnostic approximations** from a Gaia 2016.0 tangent-plane proper-motion correction to the ESA LAMOST observing MJD, without full covariance/parallax corrections or fiber-selection likelihood.

| LAMOST obsid | Catalog Gaia ID | Gaia G (mag) | Gaia-to-LAMOST target separation at observing epoch | Gaia RUWE |
| --- | --- | ---: | ---: | ---: |
| `235608062` | Huang+ original `1215223960901067520` | 15.7009 | **0.2706"** | 1.426 |
| `235608062` | ESA LRS `1215223960901067648` | 14.2824 | **1.9537"** | 1.087 |
| `844313076` | Huang+ original `2682701860879616256` | 13.9298 | **0.0904"** | 1.208 |
| `844313076` | ESA LRS `2682701860880020992` | 13.0171 | **1.2713"** | 1.533 |

In both cases the **Huang+/original Gaia ID is substantially closer to LAMOST's recorded input/fiber coordinate** at the approximate observation epoch. The ESA mirror's `gaia_g_mean_mag` field numerically matches the **ESA-designated alternate** Gaia source: G 14.2824 vs 15.7009 for the original source (difference 1.4185 mag), and G 13.0171 vs 13.9298 (difference 0.9126 mag). Thus the mismatches are **real competing catalog associations with different brightness**: not a rounding/64-bit serialization error and not merely absent Gaia source IDs. Nonetheless, a nearer Gaia star is not automatically the true spectroscopic counterpart, particularly with nearby stars, seeing, 3.3"-diameter LAMOST fiber, high spatial density and uncertain selection model. Both identifiers and their original measured fields remain retained.

[Graph: both published Gaia alternatives' positional separation](https://drive.google.com/file/d/1xiICjIJKyLF4mPupaHU1EIy6D7_fqmkg/view?usp=drivesdk).

### Nine DR8 records and measured provenance

| LAMOST obsid | Published ESA DR8 LRS observing date | ESA DR8 ID agrees with Huang+? |
| --- | --- | --- |
| `52606232` | 2012-06-15 | Yes |
| `257813193` | 2014-11-01 | Yes |
| `318809041` | 2015-02-13 | Yes |
| `447016213` | 2016-03-26 | Yes |
| `458106245` | 2016-05-12 | Yes |
| `459815059` | 2016-05-18 | Yes |
| `475114198` | 2016-11-02 | Yes |
| `570209101` | 2017-05-08 | Yes |
| `574314070` | 2017-05-24 | Yes |

These are **DR8 source-level observations and version evidence**, not a waiver of the original DR9 v2 verification requirement.

## Reproduction and archival

[GitHub Actions completed run 38157271013](https://github.com/gittenssexton/echolens-api/actions/runs/38157271013): **74 unit tests passed**, original 10,000 Gaia source snapshot rebuilt, exact four Gaia and nine DR8 sources queried, two offline replays byte-identical. Original TAP XML, request manifests, original field units and uncertainties, 4 Gaia source records, 9 DR8 records and complete derived JSON permanently archived:

[Echo Lens Google Drive — Experiment 007 original archived data (12,163-byte ZIP)](https://drive.google.com/file/d/1jX6s-bCJflIyiffKpf7qHyC9iVbWm7z2/view?usp=drivesdk).

## Remaining scientific checks

1. **Independent optical fiber identity**: For two conflicting Gaia IDs, obtain original official LAMOST DR9 v2.0 spectrum header and potentially PSF/fiber centering or calibrated spectral/magnitude likelihood; independently model full Gaia positional covariance/crowding. Carry both possible source IDs with attribution and null classification until verified.
2. **Nine ESA DR9 missing**: Retain original DR9 VizieR spectra and treat DR8 record as additional provenance, not a replacement. If necessary verify official DR9 v2.0 release FITS for exact obsids; no version assumption.
3. **Flagged `655310123`**: ESA DR9 record `offsets=1`, `offsets_v=4.89"` and matching input-fiber geometry already strongly explain 5.1201" offset; its Gaia mirror identifier remains `-9999` and the Huang+ Gaia ID must still be assessed. This is an instrumental issue, **not an electromagnetic anomaly**.
4. Only after astrophysical identities are validated should an independently labeled stellar control cohort be formed with proper exclusions of binaries, emission-line-active stars, dust, instrumental offsets, catalog-version bias, and survey selection effects.

**No changes** to production Render, main, Gaia DR3 10k observation values, WISE data, or previous experiment outcomes.
