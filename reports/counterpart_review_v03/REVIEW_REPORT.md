# EchoLens five-source counterpart and model-readiness review v0.3

Run: counterpart-review-v03. Date: 2026-10-11. This is a development continuation of infrared-feasibility-v02. The frozen 100-source pilot and its outputs remain unchanged. No photosphere fit, infrared residual, anomaly rank or technological-origin inference has been calculated.

## Decision

Use Gaia source **4461930649238469760** as the first field for developing the photosphere-fitting workflow, after quantitative association and contamination checks. It appears relatively isolated in the acquired cutouts and has the strongest W3 measurement among the four provisional references. This choice concerns engineering readiness, not scientific anomaly ranking or certification as an ordinary-star calibration control.

The other four sources need additional review before a simple static photosphere interpretation. Do not mark any of the five as a confirmed excess candidate. The original five-of-100 readiness result measures operational quality and is not revised by this qualitative review.

## Preserved evidence

Retrieved and inspected 20 approximately 90-arcsec native survey cutouts: AllWISE W1 and W3 plus 2MASS J and Ks for each source. Original response bytes, retrieval URLs/times and SHA-256 hashes are retained with five image-discovery metadata responses. All 25 response hashes validated. 2MASS images are selected by the exact catalog coadd_key and band; AllWISE images use the selected source's coadd_id. All five selected 2MASS record IDs agree with the associated key supplied by AllWISE. That agreement is internal catalog consistency, not independent confirmation.

See IMAGE_REVIEW.md for per-field visual observations and cutout_montage.png for the panels. Markers overlap at the plot scale, but this cannot validate sub-arcsecond centroids. Independent intensity stretches cannot be used to compare calibrated flux between bands. Neighbor symbols cover only the original 15-arcsec catalog cone; the wider images are not an exhaustive neighbor catalog.

## Conditional astrometric diagnostics

Propagated the Gaia four-parameter covariance in tangent-plane position and proper motion using all six supplied correlations, then combined it with the infrared catalog positional uncertainty. Gaia ra_error already includes cos(dec). Converted WISE signed co-sigma c to covariance c|c|. Converted 2MASS error ellipses using their documented position angle east of north.

The AllWISE column descriptions name an RA-coordinate uncertainty but do not explicitly settle the cosine convention for this implementation. Both coordinate-to-tangent and already-tangent interpretations are retained as sensitivity cases. No final covariance-qualified acceptance is made while this remains unresolved. First-order covariance propagation, direction-only proper motion, omitted parallax/perspective effects, catalog frame systematics and possible cross-catalog correlations also limit interpretation.

| Gaia ID | WISE radius: RA coordinate / tangent sensitivity | 2MASS ellipse radius | W3 SNR | Hypothetical exact 20% excess: measurement-only Z ceiling |
|---|---:|---:|---:|---:|
| 4310899120739084800 | 1.58 / 1.58 | 0.25 | 17.1 | 2.87 |
| 4461930649238469760 | 0.07 / 0.07 | 1.51 | 21.2 | 3.53 |
| 2224020313110506496 | 3.90 / 1.36 | 3.06 | 8.3 | 1.39 |
| 192355921445905536 | 0.83 / 0.77 | 0.40 | 5.7 | 0.95 |
| 4262211057903494912 | 1.27 / 1.27 | 2.89 | 76.1 | 12.68 |

Radii use reported random uncertainties only. The draft radius of three is a review trigger, not an independently calibrated identity rule or a one-dimensional three-sigma claim. The third source requires attention: its 2MASS radius is slightly above three, and its WISE radius strongly depends on the unresolved convention. review.json also records illustrative 50/100-mas additional isotropic error floors. These are sensitivity assumptions, not estimates of physical systematics. Chi-square tails are conditional residual checks, not association probabilities or infrared-excess significance.

## Photometric and source-type review

- **4310899120739084800:** visible crowding and W3 structure; 2MASS neighbors at 6.83 and 8.76 arcsec. Gaia GSP-Phot estimates A0=3.68 mag and log(g)=2.59. These estimates need independent checking and extinction/evolutionary-state treatment; the source is not certified as a low-extinction dwarf control.
- **4461930649238469760:** appears relatively isolated in these panels. Gaia GSP-Phot temperature, gravity and extinction are unavailable. The model will need constrained temperature, gravity, metallicity and extinction priors or external measurements, rather than invented fixed parameters.
- **2224020313110506496:** structured W3 field and covariance-review issues; Gaia estimates A0=2.57 mag. This source also overlaps the reference-only Experiment 001B and cannot be counted as an independent replication.
- **192355921445905536:** retain the W1 H artifact flag. It passed the W3-specific pilot screen, but that did not certify all WISE bands. W3 has low contrast in the display and SNR=5.7. Gaia GSP-Phot parameters are unavailable.
- **4262211057903494912:** Gaia catalog VARIABLE, saturated W1/W2, nearby 2MASS sources and Gaia estimates of high extinction/cool temperature/low gravity. Its high W3 precision does not make a static noncontemporaneous SED valid. Treat as a separate variability-model development case, not an ordinary control. 2MASS rd_flg=111 indicates different measurement provenance from the four reference sources' 222; preserve those distinctions.

Catalog parameter estimates and visual findings are evidence for review, not verified stellar classifications. Low Gaia RUWE alone does not establish a single ordinary star or absence of a companion. No source is silently removed from the frozen sample.

## Implication for the drafted hypothesis

The draft tests whether held-out W3 is compatible with a photospheric predictive distribution, with a proposed excess floor E>=0.20 and predictive Z>=5. It does not test technological origin directly.

For an exactly 20% excess, let f=sigma_obs/F_obs and F_obs=1.2 F_photo. With a perfectly known photosphere and independent observation error, the illustrative ceiling is Z=0.20/(1.20 f). Reaching five requires observed SNR>=30. All four provisional references fall below that precision at their catalog measurements. Model and calibration uncertainties can further reduce sensitivity. The sole source above this measurement-only ceiling is VARIABLE and requires separate time-dependent treatment.

This is an algebraic precision diagnostic, not an observed excess, injection-recovery result or population sensitivity estimate. It does not rule out testing larger excesses in the four references. It does show that the SNR>=5 availability screen cannot guarantee 20%-at-five-sigma sensitivity.

Keep the proposed thresholds unfrozen. Next develop band-integrated stellar-atmosphere predictions with extinction, W3/W4 held out, explicit error covariance and predictive checks. Start with the relatively isolated field, but do not infer calibration support from one object. If a subsequent development sample targets a particular precision, document and freeze its selection and resulting magnitude/color/extinction/coverage biases before inspecting residuals. Do not lower the significance threshold merely because these measurements are noisy. Independent calibration and untouched holdout sources remain necessary for a confirmatory test.

## Validation, reproduction and limits

Four new covariance tests passed; all thirteen pilot/covariance tests passed together. The previous 35-test baseline and GitHub CI for pilot commit 39b7ffcd4de5ecadf65ca1021d2d6e147b8e3aa6 passed before this addition. Input hashes and output validation are recorded in review.json/validation.json; the original pilot results and summary retain their recorded hashes.

Install requirements-review.txt, then run `python -m scripts.counterpart_review --review` and `python -m scripts.counterpart_figures`. Archived observations are sufficient; fetching is optional and separate. No live API routes, production database or Render settings changed. PR #7 stays draft and unmerged.

Remaining work includes settling the WISE uncertainty convention, systematics and chance-association calibration; quantitative PSF/background assessment with uncertainty images; single-exposure and variability review; independent stellar/reference classification; atmosphere/passband/extinction model validation; and sufficiently supported null calibration. This report does not claim those gates are complete.

## Documentation consulted

- Gaia DR3 source datamodel, including the tangent-plane RA-error definition: https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_main_source_catalogue/ssec_dm_gaia_source.html
- AllWISE column descriptions, covariance, quality and measurement flags: https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html
- 2MASS PSC errors, ellipse orientation and measurement flags: https://irsa.ipac.caltech.edu/data/2MASS/docs/releases/allsky/doc/sec2_2a.html
- IRSA native cutout interface: https://irsa.ipac.caltech.edu/ibe/cutouts.html
- AllWISE image product paths: https://irsa.ipac.caltech.edu/ibe/docs/wise/allwise/p3am_cdd/
- 2MASS image product paths: https://irsa.ipac.caltech.edu/ibe/docs/twomass/allsky/allsky/

Research log: frozen five-source review queue -> native image retrieval -> provenance validation -> conditional covariance/precision diagnostics -> assisted visual inspection -> documented model-readiness decision. No photospheric residual was examined or ranked.
