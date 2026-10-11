# EchoLens Experiment 003G — exact Gaia DR3 source-ID audit results

**Run:** [38146667656](https://github.com/gittenssexton/echolens-api/actions/runs/38146667656) — completed successfully. **Protocol frozen first:** `docs/EXPERIMENT_003_GAIA_AUDIT.md` committed before code or Gaia requests. **Data:** Original Experiment 003's 250 actual LAMOST DR9 optical-spectrum records, no sample substitution, and ten new authenticated public Gaia DR3 IRSA TAP archive responses for the **exact published IDs**.

## Outputs

| Registered measure | Observed result |
|---|---:|
| Published Gaia DR3 source IDs queried | 250 |
| Exact Gaia DR3 IDs resolved | **250** |
| Unresolved published IDs | 0 |
| Complete Gaia proper motion (pmra/pmdec and errors) | **247** |
| Missing Gaia proper-motion detail | 3 |
| Gaia-reference-epoch coordinate vs published LAMOST fiber coordinates: offsets >3" | **1** |
| Gaia-reference-epoch coordinate vs published LAMOST fiber coordinates: median angular offset | **0.2133 arcsec** |
| Gaia-reference-epoch coordinate vs published LAMOST fiber coordinates: approximate 95th percentile | **0.9126 arcsec** |
| Maximum coordinate offset | **5.1201 arcsec** |
| Gaia G difference compared with published Gaia G value >0.5 mag | **0** |

The 5.1201-arcsec offset is the published LAMOST observation `obsid=655310123`, Gaia DR3 `source_id=876451818359869824`. This is a **manual-review flag** and **not** proof that the published association is wrong: the two coordinate sets have not been propagated to a known common epoch, and LAMOST `RAJ2000/DEJ2000` denotes a celestial coordinate frame/equinox, NOT a recorded observation date. No matching radius is a justified acceptance threshold until individual LAMOST observation MJD and astrometric uncertainty are retrieved.

Three observations have incomplete Gaia proper-motion fields: `obsid=409308239`, `339606045`, and `167904063`; they remain in the data with explicit completeness flags. All 250 original LAMOST spectroscopic inferences, their uncertainties, published Gaia IDs, and status are retained.

## Reproducibility

- The source LAMOST response bytes were **restored directly from the frozen original Experiment 003 GitHub Actions artifact**, not downloaded afresh with a possibly changed archive representation.
- The exact Gaia ID queries, original VOTables, response timestamps, field metadata, checksums, manifest and results were exported. The two independent Gaia audit replays compared byte-identically.
- [Permanent Echo Lens Drive archive (490,651-byte ZIP)](https://drive.google.com/file/d/17b0fCdIvEWuC-3ho3L4PpuVXhAwQubyK/view?usp=drivesdk) contains original Gaia response files, provenance, and the 250-source audit JSON. Its GitHub [short-retention mirror](https://github.com/gittenssexton/echolens-api/actions/runs/38146667656) expires November 10, 2026.
- No original Gaia 10,000-source table, WISE observation, API route, or Render service was modified. This is a separate development cohort.

## Interpretation and next scientific gate

The exact Gaia source IDs exist for 250/250 LAMOST spectra, but **identity existence is not an independent epoch-aware optical counterpart verification**. Next retrieve source-specific LAMOST original observation epochs and coordinates from the official DR9 General Catalog, evaluate Gaia proper-motion/covariance propagation at the correct epoch, inspect the 5.12" mismatch, and check background crowding and duplicate candidates. Reclassify only on explicit recorded evidence, not on apparent outlier status.

Independent spectroscopic Teff/logg/FeH helps characterize the bright high-SNR FGK **reference candidates**. Their median apparent G ≈12.74 is far brighter than the frozen initial 10k Gaia sample ≈19.58, with zero common IDs. They cannot be called a representative or confirmed ordinary control cohort. No infrared excess, technology, anomaly score, or p-value was calculated.
