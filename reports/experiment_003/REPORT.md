# EchoLens Experiment 003 — first independently measured stellar-reference candidates

**UTC acquisition:** 2026-10-11. **Observational status:** 250 real published LAMOST DR9 optical spectra acquired through CDS VizieR and independently replayed offline. **Astrophysical control status:** NOT certified. **Survey:** Huang et al. (2024), *ApJS* 272, 6, `J/ApJS/272/6/catalog`, drawn from a 699,348-spectrum, 562,863-FGK-star, high-SNR reference library.

## Registered primary feasibility outcome

| Metric | Result |
|---|---:|
| Preregistered VizieR `recno` rows | 250 |
| Exactly retrieved / independently validated spectra | **250** |
| Unique LAMOST observation identifiers | **250** |
| Distinct published Gaia DR3 crossmatch IDs | **250** |
| Spectra passing documented spectroscopic-label readiness rules | **250** |
| Missing or invalid parameter/uncertainty/ID quality failures | **0** |
| Repeated spectra for one Gaia ID in this sample | **0** |
| Overlap with existing frozen Gaia 10,000-source pilot | **0** |

The zero overlap was a possible result established before retrieval. It is a consequence of the two very different selection frames; it does not mean the actual LAMOST stars lack Gaia DR3 measurements. **No LAMOST/Gaia source association has yet been independently verified against Gaia astrometric records.**

## Measured sample properties

| Published quantity | Min | Median | Max |
|---|---:|---:|---:|
| Gaia G apparent magnitude (mag, included with published record) | 9.451 | 12.738 | 17.227 |
| LAMOST i-band spectrum SNR | 109.12 | 201.91 | 857.68 |
| LAMOST z-band spectrum SNR | 100.47 | 150.20 | 775.18 |
| Spectroscopic Teff (K; pipeline inference) | 4,825 | 5,866.5 | 6,795 |
| Published Teff error (K) | 9 | 25 | 55 |
| Spectroscopic logg (dex, cm/s2) | 3.836 | 4.230 | 4.761 |
| Published logg error (dex) | 0.012 | 0.035 | 0.076 |
| Spectroscopic [Fe/H] (dex) | −0.873 | −0.081 | 0.442 |
| Published [Fe/H] error (dex) | 0.006 | 0.020 | 0.045 |

These are tabulations from actual archived VizieR catalog responses, NOT invented stellar measurements. Spectroscopic physical quantities are LAMOST reductions/parameter estimates and have model uncertainties beyond the published per-row formal errors.

**Severe selection mismatch:** G median 12.74 here, versus 19.58 in the full 10,000-star Gaia pilot and 15.74 in its provisional high-quality subset. The LAMOST data are **much brighter**, deliberately FGK-only and high-SNR, and cannot simply serve as controls for fainter/missing/other spectral-type Gaia targets. This survey also studies stellar activity, so individual objects may be active, variable or binary.

## Reproducibility and archival

- Preregistration frozen in first commit `5cf248627942c8553ebd30007a21e2f8544e4437` **before code or acquisition**.
- VizieR 250-spectra query performed as 10 specific queries of 25 frozen `recno` values.
- Every VOTable original, query, HTTP date, schema, units and SHA-256 saved. Gaia DR3 initial raw data SHA-256 remains `d193d7e144d5a7fc9f3d877a9323fc3c68ee2baf05b966d997392309a5248fb0`.
- [GitHub Actions run 38146071576](https://github.com/gittenssexton/echolens-api/actions/runs/38146071576) passed the original Gaia database rebuild/tests, LAMOST fetch, and two independent no-network replays with byte-identical JSON.
- [Archived original 23-file dataset and derived results in Echo Lens Drive](https://drive.google.com/file/d/17BNw9PiCM4I20DE1F5cnHS09z7GdOEqY/view?usp=drivesdk) (109,649-byte ZIP; independently verified Drive upload). GitHub's corresponding 30-day artifact expires 2026-11-10.
- Code: `python -m scripts.lamost_controls_003 --fetch` to acquire a *new* explicit snapshot in a new working folder; `python -m scripts.lamost_controls_003` for archived offline replay. Current committed serving application does not call either path.

## Next evidence gate

1. Re-query the 250 **exact Gaia DR3 IDs** through the ESA/IRSA Gaia archive and verify count, 64-bit identity, astrometry/quality, catalog uncertainties and photometry. Preserve both archives and the source identities.
2. Compare Gaia positions to LAMOST fiber positions but **do not equate J2000 equinox with actual observing epoch**. Without the LAMOST observation MJD, these associations remain epoch-unqualified. Retrieve original LAMOST DR9 general spectra observations/epochs if positional acceptance is planned.
3. Validate astrophysical natural-positive/ordinary categories with independent evidence and compare covariate coverage before designing a new matched population. The 250 pilot is an engineering success but **not a confirmed unbiased control sample**.

No anomaly score, technology inference, source redaction, Gaia-row replacement, Render change, or `main` merge occurred.
