# SP01-P2B — 20 calibration spectra acquired (2026-10-12 latest)

**Latest milestone:** 20 source-level calibration targets (5 in each preregistered stratum) independently matched by Gaia/GALAH IDs to the original GALAH DR4 `allspec` catalogue, with **20 real** single-visit analysis FITS acquired, hashed and independently replayed for descriptive red-arm fit-mask quality control. **Holdout 20/20 remain unopened**; 10 natural-positive spectra also remain unopened. Original reduced native B/R LSF verified only for the initial 2 stars; 20 further Data Central native requests returned 403. There is no calibrated star-level false alarm or discovery. [Final engineering report](../reports/sp01_p2b/CALIBRATION_20_SOURCE_ENGINEERING_RESULT_2026-10-12.md), [complete reproducibility archive](https://drive.google.com/drive/folders/1m5zxPoj4gEMJMWGJKYrxyUjiaY_f9WVd), [source catalogue policy](GALAH_DR4_SOURCE_POLICY.md).

---

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
