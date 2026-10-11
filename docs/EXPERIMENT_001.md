# EchoLens Experiment 001 — preregistration draft v0.1

## Question and scope
Can a reproducible, uncertainty-aware comparison of stellar observations identify
outliers that survive known astrophysical and instrumental explanations?
The initial Gaia registry establishes data infrastructure, not a technosignature
search result. Gaia broad-band catalog values alone cannot test artificial spectral
lines, infrared waste heat, or periodic signaling. No star is a verified lifeless
control. Stellar classification probabilities are estimates, not confirmation.

## Hypotheses
H0: observed deviations are consistent with stellar populations, dust, extinction,
binarity, variability, blending, survey selection, noise, or calibration effects.
H1: at least one source has a replicated electromagnetic deviation not explained
by the registered natural/instrumental models. H1 does not establish technology.
Later independent tests: photosphere-normalized infrared residuals; spectral
residuals at survey resolution; temporal deviations with cadence/window-function
checks; combined evidence conditional on dependencies between those measurements.

## Pilot sampling, frozen before analysis
Query Gaia DR3 gaia_source using random_index < 1,000,000 and stellar
classification probability >=0.9. Take the first 10,000 ordered by Gaia’s unique
random_index permutation; imports verify index uniqueness. Save exact ADQL and
original native catalog response and source-column metadata plus SHA-256.
The serving archive is recorded explicitly; the initial sample uses IRSA’s Gaia
DR3 mirror with native FITS measurements. Do not sort by source_id to select sky-local regions.
Keep low-SNR, negative/missing parallaxes, variable sources and poor astrometric
solutions in the registry; apply quality restrictions to control selection and
specific analyses. This is a classification-selected Gaia pilot, not a volume
complete census. Gaia's selection function and classification completeness remain
biases. The classifier's single-star category also biases coverage of white
dwarfs and binaries. Color, inferred temperature, distance and gravity coverage must be reported,
not assumed representative. A future stratified sample should define quotas before
fetching, not retrofit this sample.

## Control cohorts (to be assembled before scoring)
* Reference: independently characterized ordinary stars; provisional Gaia screen:
  parallax_over_error>=10, G<18, astrometric_params_solved in (31,95),
  RUWE<1.4, visibility_periods_used>=9, not duplicated, non_single_star=0,
  no published VARIABLE flag, G/BP/RP flux SNR>=50, and finite errors. These
  screening choices are operational, not physical boundaries; absence of a
  variability flag does not prove constant luminosity. Require later WISE
  artifact/blending checks and spectroscopic characterization. Never exclude a
  reference merely because the target anomaly score is large.
* Natural positives: independently cataloged variable stars, binaries, dusty
  stars/young objects, emission-line stars and objects with known artifacts.
  Preserve catalog classification, version and evidence for each assignment.
* Synthetic positives: inject labeled signals into copies of observations with
  realistic survey response, cadence, covariance and noise. Never put synthetic
  objects in the real-star registry or use them as discovery evidence.

Match candidate/reference stars on temperature/color, surface gravity,
metallicity, magnitude/SNR, extinction, distance, sky density and survey coverage.
Freeze matching tolerances and quality rules after feasibility assessment, before
looking at anomaly ranks. Split by stable source-ID hash (train/calibration/test
60/20/20); put known binaries, clusters and repeat observations into the same split
to prevent leakage. Freeze the split manifest and random seed. Do not claim these
cohorts are populated merely because the Gaia pilot has been imported.

## Registered analysis requirements before execution
Fit population/stellar models on training data only; use held-out reference stars
for null calibration. Propagate uncertainties and astrometric covariance, account
for magnitude/parallax systematics, censor upper limits, and retain missingness.
Do not use naive 1000/parallax as an unbiased distance. Gaia GSP-Phot parameters
and percentile intervals are pipeline inferences and must be labeled accordingly.
Epoch observations being available is not a variability detection.

Before scoring, freeze model versions, feature definitions, primary tests,
matching tolerances, injection amplitudes, power targets, and exclusions. Primary
candidate criterion: empirical calibrated p-values with Benjamini–Hochberg FDR
q<=0.01 across all tested stars/features; report dependence caveats and use a
conservative correction if required. Supplement with effect sizes and uncertainty
intervals. Require independent epochs/instruments and blinded human review of
natural explanations before assigning an unexplained-candidate status. Pilot
sample size 10,000 is an engineering target; no power claim until injection-based
sensitivity has been measured. Report false positives on natural controls and
recovery rate by SNR, stellar type and injection amplitude. Archive negative results.

## Evidence policy
Store catalog measurements, catalog inferences, reproducible derived products,
and AI interpretations separately. Every result links exact input catalog release,
source IDs, observation epochs, artifact checksum, algorithm version and parameters.
AI may propose explanations or follow-up; it cannot overwrite measurements or
supply a probability of extraterrestrial technology from an outlier score.

Sources: Gaia DR3 data model and Gaia Collaboration (Vallenari et al. 2023),
https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_main_source_catalogue/ssec_dm_gaia_source.html
https://www.aanda.org/articles/aa/full_html/2023/06/aa43940-22/aa43940-22.html
Gaia scan-angle artifacts: https://arxiv.org/abs/2212.11971
