# EchoLens SP01-P2B — Current research entrypoint

**Status updated 2026-10-12.** The P2B selection protocol remains frozen in [SP01_P2B_PROTOCOL.md](SP01_P2B_PROTOCOL.md). That document was written before the real catalogue feasibility test, so its introductory "no cohort yet" text is historical, **not** the current experiment status.

The canonical current references are:

- [Source authority and Datalink policy](GALAH_DR4_SOURCE_POLICY.md): original GALAH DR4 `allspec` is **per observation**, original `allstar` is the recommended **per-star** catalogue, crossmatch is supplemental, and original native eight-HDU camera FITS are distinct from analysis-model FITS.
- [P2B status reconciliation](SP01_P2B_STATUS_2026-10-12.md): **50 provisional real source IDs** selected using a *detrended* VizieR GALAH catalogue; **two** of the calibration stars confirmed in the **original** DR4 allspec mirror; **four** original reduced-camera FITS (two B, two R) with native LSF; four G/I camera claims still quarantined.
- [Machine-readable verified subset](../data/galah_dr4_source_registry_v1.json) and [offline validator](../scripts/galah_dr4_registry.py): source IDs, exact GALAH observation IDs, archived SHA-256, file roles, status and missing cameras.
- [Original source records and all prior findings](https://drive.google.com/drive/folders/18gx5k2UII841FJiwFBxvdMGs3GxS35yA).

**The 20 holdout sources remain untouched.** This is an engineering feasibility study, not an independent source-level false-alarm distribution, astrophysical discovery, or technosignature claim. Full original `allspec`, `allstar`, and Gaia/WISE catalogue FITS have **not** been imported in bulk.

Use the offline validator without archive downloads:

```bash
python -m unittest tests.test_galah_dr4_registry -v
python -m scripts.galah_dr4_registry --registry data/galah_dr4_source_registry_v1.json
```

The five P2B public-data acquisition workflows are manually dispatched; routine pull-request checks validate small local fixtures and provenance rules only. Do not merge this draft branch or modify Render until reviewed.
