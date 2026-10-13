# EchoLens Gaia input-readiness follow-up v0.4

Date: 2026-10-12. Source: Gaia DR3 **4461930649238469760**. Stage: development input acquisition and validation. No stellar-atmosphere fit, infrared residual, significance score or technological-origin inference is produced.

## What changed

The source chosen for its relatively isolated survey images now has a preserved, externally calibrated Gaia BP/RP spectrum and spectroscopic parameter estimates from Gaia's separate astrophysical_parameters table. The original main-catalog record lacked GSP-Phot temperature/gravity/extinction; that did not mean every Gaia parameter pipeline lacked results. The new measurements and estimates are additional provenance-bearing inputs, not replacements for the frozen registry.

This source was chosen after development inspection of W3 availability and image quality. It is development-exposed and cannot be treated as untouched holdout or an independently certified ordinary-star control.

## Acquisition and verification

Five native ESA responses are archived with request URLs, retrieval times and SHA-256 hashes:

| Response | Preserved content |
|---|---|
| gaiadr3.gaia_source | One exact source; all 152 native fields |
| gaiadr3.astrophysical_parameters | One exact source; all 226 native fields |
| 60-arcsec Gaia neighborhood | 11 sources including the target; 12 requested fields per source |
| XP_SAMPLED DataLink product | 343 externally calibrated flux/error samples from 336 to 1020 nm, every 2 nm |
| XP_CONTINUOUS DataLink product | One source; all 26 native fields, including 55 BP and 55 RP coefficients, errors, and 1,485 correlation entries per band |

Native VOTable field descriptions/units, binary data, flags and nulls are retained. Exact source and solution identifiers are text in derived JSON to avoid browser integer rounding. TAP success/overflow status and spectral source identity are checked. All five response hashes validated. Sampled fluxes are finite and reported errors are finite and positive; the wavelength grid and continuous-product array lengths agree with their declared dimensions. These are transport/schema checks, not a complete spectral quality assessment.

The frozen IRSA-supplied registry and direct ESA record agree exactly in the six compared core measurements: RA, Dec, parallax, pmra, pmdec and mean G magnitude. This is a limited consistency check; it does not claim that every field or schema is identical. The registry and original pilot outputs are unchanged.

## Spectroscopic estimates and quality flags

| GSP-Spec estimate | Median | Published 16th–84th percentile interval |
|---|---:|---:|
| Effective temperature | 5,046 K | 4,999–5,135 K |
| log(g), cgs | 3.16 | 2.85–3.39 |
| [M/H] | −0.11 dex | −0.23 to −0.04 dex |
| [alpha/Fe] | 0.04 dex | −0.01 to 0.14 dex |

The first 13 GSP-Spec quality characters are decoded in summary.json. The fluxNoise flag is 1; the other twelve parameter-quality characters are 0. Values of 9 elsewhere in the full chain refer to additional abundance/equivalent-width quality categories and must not be mistaken for a blanket rejection or acceptance of all atmospheric parameters. Retain the original chain and use-case-specific documentation.

These are catalog inferences with formal intervals, not independently established truth or a complete prior covariance. GSP-Spec assumes a single star, and possible calibration/model systematics remain. The gravity estimate supports exploring an evolved-star atmosphere rather than automatically imposing dwarf gravity; it does not establish a verified evolutionary classification.

Gaia reports has_rvs=false for the public mean RVS spectral product, while GSP-Spec parameters derived from RVS observations exist. Parameter availability and public-spectrum availability are different. No public RVS spectrum or Gaia epoch-photometry product is counted as downloaded. Both sampled and continuous BP/RP products are actually acquired and identity-validated.

## A rejected model shortcut

Gaia's Multiple Star Classifier (MSC) also supplies alternate binary-model estimates, including A0=0.41 mag and distance about 331 pc. Its flags_msc=1 explicitly marks an unreliable inference; logposterior_msc is about −16,501. Do not use its extinction/distance/components as trusted constraints, and do not infer binary membership from the existence of an MSC result or MCMC product. The entire flagged result is retained for traceability. A reliable extinction treatment is still needed.

## Optical neighborhood result

Ten other Gaia sources were returned in the finite 60-arcsec epoch-2016 discovery cone. After direction-only propagation to WISE MJD 55400, the nearest returned neighbor is **21.24 arcsec** away, with G magnitude 5.92 mag fainter (about 0.00428 of the target's G flux). No returned Gaia neighbor lies within 15 arcsec at that epoch. Three neighbors lack proper motion and retain explicitly stationary, flagged positions.

This supports the initial qualitative isolation review. It does not bound W3 contamination: optical and infrared flux ratios can differ, unresolved/uncataloged companions and diffuse emission remain possible, Gaia completeness varies, and the finite discovery cone does not guarantee inclusion of arbitrary high-motion objects at an earlier epoch. The neighbor flux ratios are optical measurements, not infrared contaminant estimates. Quantitative PSF/background assessment with image uncertainties is still outstanding.

## Spectrum and model-readiness decision

The observed spectrum and optical neighborhood are plotted in gaia_spectrum_neighborhood.png. Its shaded band shows reported pointwise flux errors. The 343 sampled points are correlated representations of continuous basis spectra, not 343 independent observations or 2-nm instrumental resolution. The continuous product preserves coefficient correlations, basis IDs, standard deviations and quality information needed for covariance-aware processing. No covariance matrix was reconstructed or inverted here.

The next modeling step can now use actual optical spectral information and reviewable GSP-Spec constraints. It still requires supported GaiaXPy calibration/covariance handling, atmosphere-library and passband validation, an extinction model, quantitative infrared contamination checks and model-discrepancy treatment. Predict W3/W4 with those bands held out. Do not count Gaia integrated photometry and the same XP measurements as independent likelihood terms without their dependence being modeled. Parameter estimates derived from Gaia data also require care to avoid reusing the same information twice.

The source's W3 precision limitation remains: at an exactly 20% hypothetical excess, its measurement-only Z ceiling is about 3.53 under the previous stated assumptions. Additional optical information does not remove the observed W3 noise. Larger excesses may be testable, but no actual excess has been evaluated and no confirmatory threshold is frozen.

## Reproduction and validation

Six new tests passed, including exact 64-bit IDs and nulls in binary VOTables, partial array masks, failed/overflow status rejection and wrong-spectrum identity rejection. All 19 readiness/covariance/pilot tests passed together. Two offline replays produced byte-identical derived outputs; hashes and runtime versions are in validation.json. The original pilot summary/results retained their recorded hashes.

Run `python -m scripts.gaia_model_readiness --replay`, followed by `python -m scripts.gaia_readiness_figures`, from an extracted package containing both archived report trees. These commands need no network access or Gaia database. `--fetch` is separate and never automatically refreshes an existing response. Local validation used Astropy 8.0.1. The repository's pinned Astropy 7.2.0 CI passed for code/test commit 3388c2f02bafa42f3f49cea1586e25ca2e6a18bb, run 38286441743; it runs offline regression tests rather than another astronomical download.

No API routes, production registry or Render settings were changed. PR #7 remains draft and unmerged. This stage resolves availability of Gaia optical spectra and some atmospheric inputs; it does not complete contamination, photosphere modeling or scientific calibration.

Documentation: Gaia AP datamodel https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_astrophysical_parameter_tables/ssec_dm_astrophysical_parameters.html ; sampled spectral datamodel https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_spectroscopic_tables/ssec_dm_xp_sampled_mean_spectrum.html ; DataLink https://astroquery.readthedocs.io/en/latest/gaia/gaia.html ; covariance-aware processing tools https://gaia-dpci.github.io/GaiaXPy-website/ .

Research log: direct ESA connection -> exact-source and AP acquisition -> finite neighborhood acquisition -> native sampled/continuous spectral retrieval -> identity/status/hash validation -> quality-flag review -> observed-spectrum/neighborhood graph -> deterministic offline replay -> archived input-readiness decision. No infrared residual was scored.
