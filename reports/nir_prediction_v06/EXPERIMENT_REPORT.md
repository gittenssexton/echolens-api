> **SUPERSEDED INTERPRETATION — 2026-10-13:** The 32–34% W3 shortfall below was reproduced as a sparse-wavelength linear-flux interpolation artifact. It is not evidence for a physical deficit. PHOENIX and shape-preserving CK04 interpolation predict W3 close to the observation. See [v0.7–v0.9 correction report](https://drive.google.com/file/d/11tZwHNyB8XND1Y7jYE-AxnPUqvqhqLa1/view?usp=drivesdk). Original observations and rejected numerical outputs are retained for audit.

# EchoLens NIR-only held-out W3 pilot v0.6

Run `nir-heldout-w3-v06`, 2026-10-13 UTC. Gaia DR3 source **4461930649238469760**. Exploratory development experiment, not an independent replication or calibrated anomaly test.

## Result

The near-infrared-only fit predicts **W3 = 9.64756 mag**, while the archived AllWISE observation is **10.07800 ± 0.05100 mag**. Observed/predicted in-band flux is **0.67271**, a conditional residual of **−32.73%**. Across the stated stellar/extinction sensitivity cases the residual spans **−33.86% to −32.22%**. This result points in the opposite direction to the proposed infrared-excess hypothesis. It does not establish a physical flux deficit: atmosphere-model discrepancy, noncontemporaneous variability, calibration and measurement effects remain unresolved.

No calibrated probability, p-value, technological-origin inference, anomaly ranking or ordinary-control certification is assigned. The sensitivity envelope is not a confidence interval, and the quoted W3 uncertainty excludes the unresolved predictive uncertainties.

## Question and scope amendment

Working hypothesis: does held-out W3 exceed a stellar-photosphere prediction constrained by shorter wavelengths? The eventual null is compatibility with a calibrated photospheric predictive distribution; the draft excess floor is 20%. This reduced pilot tests integration and conditional prediction using **only J/H/Ks for fitting**, while optical Gaia forward-response modeling remains deferred. It cannot complete the confirmatory Gaia-plus-NIR test.

The design manifest was written before fitting/comparison in this run. The source and W3 values were already exposed during development, so this is a held-out *fitting band*, not blinded data. The source was selected for measurement readiness/isolation from a quality-screened sample; it is not representative or independent calibration data.

## Data and model

Real catalog observations: 2MASS J/H/Ks = 10.69500/10.16600/10.13300 mag, combined errors 0.01900/0.02750/0.02330 mag. W3 is excluded from normalization/extinction fitting. W4 = 8.89000 is a **95% flux upper limit**, never a Gaussian detection or fit datum. All model W4 predictions are fainter than this limit; that provides only a weak consistency check.

Theoretical inputs: six archived STScI Castelli–Kurucz CK04 atmosphere tables. Linear surface-FLAM interpolation in temperature (4750/5000/5250 K), gravity (2.5/3.0/3.5), metallicity (−0.5/0). Exact native-grid recovery is checked; interpolation accuracy against additional atmosphere nodes is not established. Every model retains provenance and raw SHA-256 checks. Models are never stored as stellar observations.

Synthetic photometry integrates each spectrum against native SVO response curves. Metadata DetectorType=1 for 2MASS uses ∫Fλ λ R dλ; DetectorType=0 for WISE uses ∫Fλ R dλ. Vega denominators use archived CALSPEC alpha_lyr_stis_011 FLAM/Angstrom data, assigned zero magnitude per band. Constants cancel in ratios. Native response knots plus 4000 log-spaced points form the integration grid. Both spectra cover the full responses. G23 extinction is evaluated only over the passbands, with wavelength units supplied explicitly.

Conditional parameter cases: temperature 4999/5046/5135 K, logg 2.85/3.16/3.39, [M/H] −0.23/−0.11/−0.04, from Gaia GSP-Spec summaries. These 27 combinations are sensitivity cases, not a joint posterior sample; correlated parameter uncertainty is not represented. Rv=2.5/3.1/4.0 yields 81 cases. Each is repeated with Av allowed 0–0.3 and 0–1.0 mag at 0.005 steps (162 total fits). Dust-map full-line-of-sight context is not imposed as a stellar prior or hard bound; unreliable Gaia MSC extinction is not used.

Normalization is an analytically profiled additive magnitude offset. Reported combined JHK errors are conditionally independent Gaussian magnitude errors; zero-point covariance and model discrepancy are not modeled. Three fitted bands offer little information about extinction. A grid optimum is not a posterior estimate.

## Fit and sensitivity

Central parameters 5046 K/logg3.16/[M/H]−0.11/Rv3.1 give Av=0.115 mag and JHK chi-square=0.95658; predicted J/H/Ks=10.69077/10.18920/10.12271. No fit-probability claim is made.

| Allowed Av | Cases | Best-fit Av range | Boundary cases | JHK chi-square range | W3 prediction range |
|---|---:|---|---:|---|---|
| 0–0.3 | 81 | 0–0.3 | 13 | 0.588–1.690 | 9.62913–9.65571 |
| 0–1.0 | 81 | 0–0.37 | 3 | 0.588–1.635 | 9.62913–9.65571 |

Widening extinction removes ten upper-bound optima but does not change the W3 envelope. Lower-bound fits remain. These boundaries reinforce weak extinction identification.

An alternative reference sensitivity normalizes each band to a flat Fnu spectrum at its SVO catalog zero point. Central W3 then becomes **9.64500**, versus 9.64756 in the CALSPEC calculation. This numerical agreement is not independent empirical calibration. The WISE documentation uses an ideal Vega basis, plus a separate W4 adjustment, so survey-specific reference matching remains a required gate. The archived flat-Fnu check and integrated/monochromatic context explicitly distinguish in-band from monochromatic quantities; no extra monochromatic color correction is applied to in-band ratios.

## Verification and replay

Five analytic unit tests passed: energy/photon weighting, Vega self-zero and scaling, missing coverage/negative flux rejection, weighted normalization and held-out-band independence. A separately labeled noiseless synthetic injection recovers Av=0.12 and normalization=50; these synthetic values are validation fixtures, not registry stars. Doubling quadrature density changes magnitudes by at most 2.56e−7 mag for the central case at Av=0/0.3/1. This validates numerical quadrature on the adopted interpolated spectra, not the physical spectral resolution or model.

Socket network access was blocked during replay, and fit/summary/comparison JSON outputs repeated byte-identically. New response and model hashes were verified. See validation.json for exact dependency versions. The archive contains original catalog/model/filter/Vega data, query provenance, design, outputs, code/tests and diagnostic figure. No refresh is required.

From archive directory echolens:

```
python -m pip install -r requirements-nir.txt
python -m pytest tests/test_nir_prediction.py -q
python -m scripts.nir_prediction
python -m scripts.nir_prediction_figures
```

## Decision and next experiment

Do not designate this source an excess candidate or control, and do not promote this conditional residual to significance. The next gate is a calibration/model-discrepancy experiment: reproduce survey reference conventions, compare an independent atmosphere family, and test W1/W2 predictions plus quantitative W3 background/PSF measurements. These additional bands must remain explicitly separate validation diagnostics. After that, freeze the full predictive model and validate it against independently selected ordinary stars before scoring the science sample.

PR #7 remains draft/unmerged; Render and the live API are unchanged.

## Primary references

- [STScI CK04 model grid](https://ssb.stsci.edu/trds/grid/ck04models/)
- [STScI CALSPEC archive](https://ssb.stsci.edu/cdbs/calspec/)
- [SVO filter service](https://svo2.cab.inta-csic.es/theory/fps/): exact requests and native metadata in acquisition_manifest.json/raw.
- [G23 dust_extinction 1.7](https://dust-extinction.readthedocs.io/en/stable/api/dust_extinction.parameter_averages.G23.html)
- [WISE calibration, in-band photometry and color corrections](https://irsa.ipac.caltech.edu/data/WISE/docs/release/All-Sky/expsup/sec4_4h.html)
- [2MASS relative spectral response](https://www.ipac.caltech.edu/2mass/releases/allsky/doc/sec6_4a.html#rsr)
