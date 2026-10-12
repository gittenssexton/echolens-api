# EchoLens Gaia covariance and model-input audit v0.5

Date: 2026-10-12. Development source: Gaia DR3 **4461930649238469760**. This stage validates numerical uncertainty propagation and prepares atmosphere inputs. It does not fit a photosphere or calculate an infrared residual, p-value or technological-origin interpretation.

## Outcome

The full-coefficient flux and pointwise errors have been reproduced using GaiaXPy 2.1.4. A problem in its combined-band correlation output was isolated, and a separately tested adapter now propagates the two band covariances with weights on both axes. Original package code and catalog observations are unchanged; the rejected result is preserved.

The corrected dense spectrum covariance is positive semidefinite within floating-point tolerance but numerically rank-deficient. A 32-point development grid is positive definite and passes Cholesky decomposition without jitter. This makes a correlated numerical likelihood possible; it does not validate a stellar model or justify discarding calibration/model uncertainty.

## Reproducible covariance finding

The public `calibrate(..., with_correlation=True)` result for the full 343-point grid produced a combined correlation whose reconstructed covariance had a minimum/maximum eigenvalue ratio of **−0.00087047**. This is too large to dismiss as floating-point roundoff; our positive-semidefinite gate rejects it.

The installed GaiaXPy 2.1.4 implementation was inspected. In its combined-band covariance merge, a single merge-weight vector is broadcast across one matrix axis. Correct propagation for wavelength-dependent weights requires both axes:

\[C_{\rm merged}=W_{\rm BP}C_{\rm BP}W_{\rm BP}+W_{\rm RP}C_{\rm RP}W_{\rm RP},\]

where W is the diagonal matrix of band weights. This expression assumes zero cross-band covariance. Any additional BP/RP cross-covariance or calibration dependence remains outside this engineering audit.

The adapter obtains each band through GaiaXPy's public single-band calibration path and performs the tested linear merge separately. The installed version, implementation file hash and calibration-configuration hashes are recorded. It requires version 2.1.4 and will fail if another version is installed; this is a version-specific finding, not a claim about all GaiaXPy releases. No external bug report or upstream change was made.

The corrected result matches the public combined **mean flux and pointwise errors exactly**. It differs only in the propagated joint covariance. Relative to the separately acquired native archive spectrum, the maximum mean-flux difference is **0.00954 of a reported pointwise error**, and the maximum fractional error difference is **0.000220**. The archive observations remain unchanged.

The original coefficient covariances are well behaved; the failure was identified in the calibration merge rather than interpreted as a stellar signal. All working matrices are retained in full. No negative-eigenvalue clipping, diagonal jitter or invented error floor is applied.

## Sampling and truncation audit

| Representation | Wavelength samples | Numerical rank at relative 10⁻¹⁰ | Minimum/maximum eigenvalue ratio | Direct Cholesky without jitter |
|---|---:|---:|---:|---|
| Rejected combined-correlation output | 343 | 92 | −8.70×10⁻⁴ | Rejected |
| Correct two-axis merge, all coefficients | 343 | 90 | −2.33×10⁻¹⁶ | No: rank deficient |
| Correct merge, recommended 20 BP / 12 RP bases | 343 | 32 | −1.26×10⁻¹⁶ | No: rank deficient |
| Correct merge, all coefficients, 380–1000 nm every 20 nm | 32 | 32 | +5.79×10⁻⁴ | Yes |

Ranks are numerical diagnostics, not independent-observation counts or astrophysical degrees of freedom. For the full grid, the reported rank varies from 84 to 93 as the relative cutoff changes from 10⁻⁶ to 10⁻¹²; these results are retained. Singular covariance in an oversampled basis representation is expected. A fitting method must work in a justified coefficient/subspace representation or use a validated sampling and discrepancy model.

The recommended truncation changes the mean by a median **0.565** and maximum **3.01** full-spectrum pointwise error units. These are processing comparisons, not independent significance tests or excess measurements. Truncation is preserved as a separate case; neither it nor the coarse grid has been frozen as a confirmatory scientific policy. The 32-point grid was evaluated for numerical conditioning on development data, not selected from infrared residuals.

## Independent dust-map context

A successful IRSA DUST XML response is preserved for the source's coordinates. The reference-pixel E(B−V) values are **0.0542 mag** for the Schlafly/Finkbeiner scaling and **0.0631 mag** for SFD. These are two map prescriptions, not the endpoints of a confidence interval. Spatial standard deviations in the surrounding five-arcminute area are not stellar extinction uncertainties.

These are two-dimensional full-line-of-sight dust-map estimates, not a finite-distance extinction measurement for this star. An illustrative R_V=3.1 multiplication would give A_V about 0.168 and 0.196 mag; it is not a fixed A0 or an adopted fitting prior. The previous Gaia MSC extinction inference remains flagged unreliable. Extinction law, distance dependence, map uncertainty and potential source-model degeneracy still need explicit treatment.

## Atmosphere inputs now preserved

Six native Castelli–Kurucz/ATLAS9 atmosphere FITS files were acquired from STScI's public archive:

- Temperatures 4,750, 5,000 and 5,250 K, at each of [M/H]=−0.5 and 0.0 dex.
- Gravity columns log(g)=2.5, 3.0 and 3.5 were checked; the complete original multigravity files remain intact.
- Each file contains 1,221 ordered wavelength samples spanning 90.9–1,600,000 Angstrom, with finite nonnegative model values in the checked gravity columns. FITS temperature/metallicity headers agree with the requested cells.

These bracket the earlier GSP-Spec estimates sufficiently to begin a local interpolation assessment. They are explicitly **theoretical surface-flux models**, not catalog observations, artificial stars inserted into the registry, or fitted results. Their headers specify erg s⁻¹ cm⁻² Angstrom⁻¹ surface flux; scaling to received flux requires a justified normalization. Wavelength coverage alone does not validate passband integration, grid interpolation, atmosphere adequacy or Gaia's response/line-spread handling.

The first directory-index request timed out, but direct native model-file downloads succeeded and their hashes/headers were checked. Only these six small files were acquired, not a full atmosphere collection or survey. The dust XML and model inputs retain their URLs, retrieval times, original bytes and separate provenance classifications.

## Validation and reproduction

Seven new analytic unit tests passed, covering packed-correlation ordering, covariance weights on both axes, zero-weight out-of-band values, rejection of indefinite/asymmetric matrices, rank-deficiency distinction and invalid-input rejection. All **26 covariance/readiness/pilot tests passed together**. GitHub CI passed for code/test commit 82013aa22b7280d9e3c701d843db0d4018f715dc, run 38303349021. This CI checks offline units/regressions; the real-source GaiaXPy calibration is separately recorded as a local integration check.

Repeated calibration produced byte-identical arrays and a byte-identical summary. A socket guard blocked network connections during processing. The coarse matrix passed an actual Cholesky decomposition. The archived input spectrum hash stayed `973de62f3a4611c007978b6f95c276b8d7309ac577c78262f237bfa856784937`.

Install requirements-xp.txt and run `python -m scripts.xp_covariance`, then `python -m scripts.xp_covariance_figures`. Calibration operates on archived local coefficients. `xp_model_context` is a separate acquisition script; existing model files are checksum-validated and reused. Runtime versions, package-configuration hashes, rejected output, corrected matrices, graph, native model/dust inputs and validation log are included.

## Next scientific gate

Develop the atmosphere likelihood with supported Gaia response handling, an explicit extinction model and quantitative infrared contamination review. Validate passband integration and normalization using optical/near-infrared information, while keeping W3/W4 out of fitting. Do not double-count the same XP data and derived Gaia photometry/parameters as independent measurements. Model/calibration discrepancy and cross-band dependence require assessment even though the numerical covariance is now usable.

No photosphere, infrared residual or discovery score is computed here. The source remains development-exposed, and its W3 precision still does not guarantee 20%-at-five-sigma sensitivity. No live API, production registry or Render configuration changed. PR #7 stays draft and unmerged.

Documentation and model sources: GaiaXPy 2.1.4 calibration source/API https://gaiaxpy.readthedocs.io/en/2.1.4/_modules/gaiaxpy/calibrator/calibrator.html ; STScI atlas documentation https://stsynphot.readthedocs.io/en/latest/stsynphot/appendixa.html ; archive https://archive.stsci.edu/hlsp/reference-atlases ; IRSA DUST API https://irsa.ipac.caltech.edu/applications/DUST/docs/dustProgramInterface.html .

Research log: archived-input recovery and checksum verification -> public combined calibration -> covariance rejection -> independent-band diagnosis -> tested two-axis merge -> grid/truncation sensitivity -> offline reproducibility -> dust/model acquisition and validation -> documented modeling gate. No infrared residual was inspected or ranked.
