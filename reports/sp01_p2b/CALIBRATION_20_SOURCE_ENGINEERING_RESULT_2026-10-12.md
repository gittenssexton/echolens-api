# EchoLens SP01-P2B — 20-source calibration-only GALAH DR4 engineering report

**Date:** 2026-10-12. **Research status:** completed original-release cross-identification and acquisition of 20 in-sample analysis spectra. This is **not** a source-level FAP-calibrated test, not a discovery scan, and contains **zero held-out observations**.

## Acquisition and identities
- Frozen provisional source-list SHA-256: `ef62ec0bd5afd79a8c39613f2796943937dd09d9eb6e6bfabe644522e2beed32` (Kos et al. detrended DR4 VizieR table, with roles frozen before spectra were downloaded).
- 20 distinct Gaia DR3 sources across four temperature and SNR strata, five per stratum; no reuse across groups.
- All 20 GALAH observation IDs and associated Gaia source IDs independently checked against Buder et al. original GALAH DR4 `allspec` **CDS/VizieR distribution** (two real original-catalogue response subsets preserved with SHA).
- 20 survey-hosted original **analysis-product** FITS files downloaded and original byte hashes recorded; 2 were obtained in the earlier pilot and 18 in the two acquisition runs. These are `single_fit_spectrum.fits` *observed flux plus fitted model and mask*; they are not the original 8-HDU reduced cameras.
- 4 original 8-HDU reduced-camera FITS products (blue and red for the first two stars) are archived separately in this package with measured wavelength-dependent LSF. All green and near-IR original-camera claims remain unavailable/quarantined.
- [First 8 source expansion GitHub workflow](https://github.com/gittenssexton/echolens-api/actions/runs/38293188168): original ID 8/8; six new FITS validated; native requests HTTP 403.
- [Remaining 12 source expansion workflow](https://github.com/gittenssexton/echolens-api/actions/runs/38293762472): original ID 12/12; all 12 new analysis FITS validated.

## Descriptive model-fit comparison (red camera only)
An engineering quality-control measurement was computed over 4,096 red-arm pixels per observation, **81,920 pixels total**; per-pixel z=(observed−pipeline same-observation model)/(quoted uncertainty). The `mob` flag describes pixels retained/excluded by the **same-data model fitting**; it is *not* independent detector quality information. Fit-excluded pixels are a selected group biased toward larger residuals.

| Calibration stratum | Stars | Median |z|>5 in fitted pixels | Median |z|>5 in excluded pixels |
|---|---:|---:|---:|
| cool_low | 5 | 0.025% | 16.08% |
| cool_high | 5 | 0.329% | 27.97% |
| warm_low | 5 | 0.000% | 15.69% |
| warm_high | 5 | 0.076% | 21.23% |

Across 20 stars, median large-residual share in fit-retained red pixels = **0.051%** (range 0.000–0.582%), compared with median **18.81%** (range 5.04–45.83%) in excluded pixels. This pattern demonstrates fitting/masking selection and does **not** establish anomalous emission, true statistical significance or a rare-event false-positive probability.

## The native-camera access issue remains open
After earlier successful GALAH DR4 Datalink retrievals for four B/R files, **all 20 later native retrieval and mapping probes** in the first eight-star expansion (including B/R, `FILT=V`, G, I and IR) returned HTTP 403 with the same short access-denied response. The underlying cause was not established; the earlier successful FITS are preserved. We will not relabel ambiguous responses or invent missing per-visit LSF. Resolve by a verified provider delivery method, not repeated blind guessing of URL parameters.

## Scientific limitations and next gate
- No prospective source-level detection threshold or false-alarm probability has been calibrated. Observed-model comparisons are circular because the model was fit to the measured data.
- 20 calibration stars give coarse resolution for nonparametric tail probabilities. The 20 **held-out** stars and 10 chemically peculiar natural positives remain unscored.
- The provisional source selection came from a detrended catalogue; only the **20 exact original-release source identities**, not all numerical star-level measurements, have been independently reconciled here.
- Preserve these 20 calibration measurements and prepare a preregistered, correlated-pixel-aware source-level score before any holdout spectra are opened. Any future candidate needs independent instrument/epoch checks and complete background/error treatment.

## Reproduction
Unzip. All 20 original downloaded FITS and four verified native camera FITS are provided, along with SHA-256 checksums. To regenerate the descriptive plot and tables, run `python p2b_twenty_spectra_qc.py` with NumPy and Matplotlib installed. Verify `sha256sums.txt` before processing; the new `reproduced_analysis/` directory can be generated independently from archived `analysis/`. Complete acquisition evidence is in `provenance/`.
