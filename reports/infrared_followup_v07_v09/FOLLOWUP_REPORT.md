# EchoLens infrared follow-up: correction of the v0.6 W3 discrepancy

2026-10-13 UTC. Source Gaia DR3 **4461930649238469760**. Three development experiments: `model-and-band-validation-v07`, `wavelength-sampling-audit-v08`, `W3-aperture-background-audit-v09`.

## Finding and correction

**The earlier 32–34% W3 shortfall is a reproducible wavelength-interpolation artifact, not evidence for a stellar flux deficit.** The v0.6 pipeline linearly interpolated surface Fλ across a large gap in the CK04 infrared wavelength grid. That interpolation overestimated the in-band photospheric flux. Refining the integration grid in v0.6 could not detect this error because it integrated the same distorted interpolated spectrum more accurately.

The CK04 wavelength table has nodes near 10.02 and 20.00 µm with no intermediate samples. A steeply falling infrared spectrum interpolated linearly in Fλ across that gap produces a large spurious flux hump. The source's real catalog measurements were not changed. Original v0.6 outputs are retained as rejected processing evidence and must not be interpreted as a physical deficit.

A second atmosphere family, PHOENIX, predicts W3 within 1–3% of the observed flux across the tested conditional cases. A controlled experiment degrades that same PHOENIX spectrum onto CK04's sparse wavelength nodes: the former ~32% shortfall reappears with linear-flux interpolation. Log-flux/log-wavelength and λ⁴-scaled interpolation restore predictions close to the dense-spectrum reference. This isolates a numerical mechanism without changing the star's input observations.

No calibrated significance, excess candidate, technological-origin inference or ordinary-control certification is assigned. A match on one development-exposed source is not empirical calibration of a predictive distribution.

## Experiment v0.7 — model family and held-out bands

Fit only the archived 2MASS J/H/Ks measurements. W1, W2 and W3 remain diagnostic bands excluded from fitting; W4 remains a flux upper limit. Reuse the v0.6 temperature/gravity/metallicity cases and test Rv=2.5/3.1/4.0 with Av=0–1 mag at 0.005 steps: **81 CK04 and 81 PHOENIX fits**.

Preserve eight native PHOENIX FITS files, at temperatures 4900/5000/5100/5200 K and metallicities −0.5/0. Model columns g25/g30/g35 provide the gravity interpolation. Validate native units, parameter headers, finite/nonnegative flux, wavelength coverage and response hashes. The PHOENIX files' wavelength grids differ; interpolate their spectra onto their common union before parameter interpolation. Every native wavelength knot is also included in each band integration grid, along with response and Vega knots and a dense auxiliary grid.

Both model families are theoretical. This is a model-family sensitivity comparison, not independent observations or independent posterior samples. PHOENIX's metallicity −0.5 files have ALPHA=+0.2, while the solar files have ALPHA=+0.0. Linear metallicity interpolation therefore changes the abundance mixture as well as [M/H]; it is not a pure fixed-abundance model comparison. No extra Gaia alpha constraint is fitted. Both families are interpolated linearly in flux across atmospheric parameters, separately from wavelength interpolation.

| Linear-flux wavelength processing | Central W1 residual | Central W2 residual | Central W3 prediction | Central W3 residual | W3 sensitivity envelope |
|---|---:|---:|---:|---:|---:|
| CK04, rejected for sparse IR grid | +4.92% | +4.56% | 9.64756 mag | −32.73% | −33.86 to −32.22% |
| PHOENIX, dense native grid | +5.23% | +4.10% | 10.06310 mag | −1.36% | −2.99 to −0.89% |

Residual means observed/predicted in-band flux minus one. These envelopes represent parameter-case sensitivity, not confidence intervals. Catalog W3 is **10.07800±0.05100 mag**, corresponding to a measurement-only fractional error of about 4.7%; this does not include predictive model/calibration errors. No residual significance is calculated.

The central PHOENIX fit has Av=0.030 and JHK chi-square=0.90349. Its 81 cases span Av=0–0.25 and chi-square 0.786–1.467; 27 hit Av=0. Extinction remains weakly identified. Both families' W1/W2 residuals of several percent remain to be empirically calibrated; they are not confirmed excesses.

Doubling the auxiliary integration grid changes the central PHOENIX magnitudes by at most 1.11e−7 mag at Av=0/0.3/1. This verifies quadrature on the adopted spectra, not physical model adequacy. A separately labeled 5046 K Planck-spectrum shape check reaches the Av upper bound and has JHK chi-square about 31.1. It does not fit the NIR data adequately and cannot replace a stellar atmosphere.

## Experiment v0.8 — controlled wavelength degradation

Use central atmospheric parameters 5046 K/logg3.16/[M/H]−0.11, Rv3.1 and profile the same Av/normalization. Resample the dense PHOENIX spectrum onto CK04 nodes without extrapolating beyond common coverage, then integrate with three wavelength interpolation prescriptions.

| Spectrum | Wavelength interpolation | Predicted W3 | Residual |
|---|---|---:|---:|
| PHOENIX native | linear Fλ | 10.06310 | −1.36% |
| Same PHOENIX degraded to CK04 nodes | linear Fλ | 9.65234 | −32.43% |
| Same degraded PHOENIX | log Fλ/log λ | 10.06113 | −1.54% |
| Same degraded PHOENIX | λ⁴-scaled flux | 10.06218 | −1.45% |
| CK04 native nodes | log Fλ/log λ | 10.05652 | −1.96% |
| CK04 native nodes | λ⁴-scaled flux | 10.05742 | −1.88% |

The model-degradation experiment reproduces the error using the same underlying spectrum. A separate 27-case stellar-parameter check at fixed Rv3.1 gives CK04 log/log residuals **−3.10 to −1.29%**. This narrower check is not the full 81-case Rv grid. Alternative interpolation cannot restore molecular features missing between native CK04 nodes; dense PHOENIX provides the explicit reference for this development check. No interpolation prescription is frozen as a final science policy.

Analytic validation uses a Rayleigh–Jeans λ⁻⁴ spectrum on sparse 10/20-unit nodes: log/log and λ⁴-scaled interpolation recover the exact shape, while direct linear Fλ strongly overpredicts intermediate flux. Zero flux is rejected for logarithmic interpolation within supported ranges; irrelevant zero UV flux is not used when interpolating a positive IR segment. Coverage outside native support is rejected.

## Experiment v0.9 — W3 aperture and background

Retrieve and preserve a **180-arcsec native W3 Atlas cutout**, extending the earlier 90-arcsec image so the documented 50–70-arcsec background annulus fits. The selected Gaia/WISE association and catalog source are unchanged. Image WCS places the catalog coordinate at pixel (65.175,65.899); pixel scale is 1.375 arcsec. BUNIT=DN; header MAGZP=18.0.

Use an 8.25-arcsec aperture with 8×8 pixel supersampling, giving effective area 113.094 pixels. Estimate background with a 3-sigma-clipped median, five iterations, in three annuli. Reuse the source's catalog curve-of-growth correction **0.825 mag**; it is not independently calibrated here.

| Sky annulus | Background median (DN) | Net aperture flux (DN) | Corrected W3 magnitude |
|---|---:|---:|---:|
| 25–40 arcsec | 462.0981 | 664.7643 | 10.11833 |
| 40–55 arcsec | 462.0637 | 668.6608 | 10.11199 |
| 50–70 arcsec | 462.0176 | 673.8689 | 10.10356 |

The standard-size-annulus result differs from catalog standard aperture **10.10500±0.06800** by only −0.00144 mag. The background choices span 0.01477 mag. Catalog profile-fit magnitude is 10.07800, 0.02700 mag brighter than its standard aperture. This does not reveal a W3 photometric shift remotely as large as the former 0.43-mag model discrepancy.

Catalog aperture flag is zero for the standard/first two apertures; larger apertures 3–8 carry source-confusion flags and must not be treated as clean flux estimates. The profile-fit reduced chi-square is 0.9594. An internal mean of individual-frame fits is 10.077, 0.001 mag from the preferred profile value, but the survey explicitly treats that mean as an internal repeatability diagnostic rather than a replacement measurement. These statistics share underlying images and are not independent replication.

Fifteen W3 frames span MJD55252.3761–55253.5008, about 1.125 days. Their internal diagnostics do not exclude longer-term variability between the 2MASS and WISE epochs. Sigma clipping does not replace a complete source mask. Atlas resampling correlates image noise; no per-pixel covariance/error/coverage model, PSF subtraction or formal uncertainty/significance is derived. Catalog aperture correction reuse also prevents this being an independent absolute calibration. Background differences are sensitivity checks, not uncertainties.

## Validation, disposition and replay

Nine focused tests passed: five inherited photometric checks and four new sampling/aperture tests. Image flux injection and uniform-background subtraction are explicitly synthetic fixtures. The 27-case corrected CK04 calculation ran with socket connections blocked. Native new-response/model/image SHA-256 hashes are retained and checked by replay scripts. Plot inspected for readability and correct magnitude direction.

Keep the legacy v0.6 numerical output reproducible, but mark its physical interpretation superseded. Add these development code/reports to draft PR #7, leaving it unmerged. No live API, production registry, Render setting, original catalog observation, frozen selection or control-group label changes.

Replay from the archive's echolens directory:

```
python -m pip install -r requirements-nir.txt
python -m pytest tests/test_nir_prediction.py tests/test_sampling_audit.py -q
python -m scripts.model_validation
python -m scripts.sampling_audit
python -m scripts.wise_image_audit
python -m scripts.infrared_followup_figures
```

The archive preserves native model/filter/image bytes and v0.6 replay dependencies. Model comparison can take several minutes. No download is needed for replay. The 27-case additional corrected-CK sensitivity output is preserved separately; its scope is explicitly stated in the JSON.

## Next scientific gate

Freeze a wavelength-resolution/integration adequacy rule validated by spectrum degradation before scoring new stars. Then select ordinary calibration sources independently of held-out W3 residuals and validate band-specific predictive errors, zero-point covariance, atmosphere-family discrepancy and coverage. Incorporate Gaia optical spectra only after forward-response modeling is validated. A candidate claim requires a calibrated predictive distribution, contamination/variability checks and independent follow-up. More tests remain possible; these completed stages do not exhaust the research program.

## Primary references

- [STScI PHOENIX native model archive](https://ssb.stsci.edu/cdbs/grid/phoenix/): native README/FITS headers and exact URLs/hashes are archived.
- [STScI reference-atlas release notes](https://archive.stsci.edu/hlsp/reference-atlases): documents PHOENIX sampling updates.
- [STScI CK04 grid](https://ssb.stsci.edu/trds/grid/ck04models/)
- [CALSPEC](https://ssb.stsci.edu/cdbs/calspec/)
- [SVO responses](https://svo2.cab.inta-csic.es/theory/fps/)
- [G23 extinction](https://dust-extinction.readthedocs.io/en/stable/api/dust_extinction.parameter_averages.G23.html)
- [AllWISE source-field documentation](https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html): standard aperture, sky annulus, correction, flags and repeatability diagnostics.
