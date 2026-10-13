# EchoLens development image audit v12

## Outcome

Nine fixed development stars were reviewed in 18 native AllWISE W1/W3 intensity cutouts, each 180 arcsec wide. Three native 90 arcsec 2MASS J/H/Ks cutouts were also acquired for the weakest v11 J/H/Ks fit. Every response has a recorded URL, acquisition time and SHA-256 hash. The eight reserved stars remain unscored. No star was replaced, no zero point or empirical scatter was fitted, and no ordinary-control or technosignature classification was assigned.

Four stars have an existing AllWISE W3 standard-aperture confusion flag. W3 profile-fit eligibility in v10 did not require that aperture flag to be zero. These are separate estimators: the aperture flags constrain use of aperture diagnostics and do not by themselves prove the profile-fit flux is wrong. Retain the stars and flags for explicit follow-up.

## Approximate W3 aperture and background checks

The frozen design uses an 8.25 arcsec radius, 8x8 fractional pixel integration, a 3-sigma clipped median sky, and three annuli: 25–40, 40–55 and 50–70 arcsec. Corrected magnitude is MAGZP - 2.5 log10(net DN) - catalog w3mcor. Band/tile/units/header and raw hashes are verified; all annuli lie inside the cutouts. The AllWISE supplement specifies the 8.25 arcsec aperture, 50–70 arcsec reference sky and subtraction of w3mcor. Our median-sky diagnostic is an approximation, not a reproduction of every catalog processing step.

| Gaia DR3 source_id | W3 aperture flag | Sky-choice spread (mag) | 50–70 result minus catalog aperture (mag) | 50–70 result minus profile fit (mag) |
| --- | ---: | ---: | ---: | ---: |
| 2759006524739613056 | 0 | 0.006701 | -0.000693 | +0.032307 |
| 3075599868480948992 | 0 | 0.010973 | -0.000043 | +0.023957 |
| 2433664848010750848 | 1 | 0.014557 | +0.001309 | +0.028309 |
| 2984872253470024576 | 1 | 0.005915 | +0.001289 | -0.022711 |
| 1742112230738093312 | 0 | 0.015609 | +0.000203 | +0.016203 |
| 2336863054027651456 | 0 | 0.007084 | +0.000842 | +0.007842 |
| 6669301637583655168 | 0 | 0.008594 | -0.000901 | +0.021100 |
| 2151835210082468992 | 1 | 0.004984 | +0.000136 | +0.014136 |
| 3657301580397050240 | 1 | 0.003489 | -0.000593 | +0.008407 |

The largest absolute difference from the catalog standard aperture is 0.001309 mag. Sky-choice spread is 0.003489–0.015609 mag. Approximate aperture-minus-profile differences span -0.022711 to +0.032307 mag. The small aperture reproduction difference checks implementation consistency using the same Atlas observations and catalog aperture correction; it is not an independent confirmation. Background-choice spread is a sensitivity diagnostic, not a measured uncertainty or detection significance. Image covariance, pixel mask/uncertainty products, local background source masks and PSF deblending have not been modeled.

## Visual review

The three W1/W3 panels were visually inspected. Display stretches are independent and cannot be used for flux/color comparisons. W1 images are morphology context only, including stars with saturated or poor W1 photometry. None of the panels provides a clearance against unresolved blending.

- 2759006524739613056: centered compact source; other field sources, including a bright W3 source near the upper cutout edge. W3 aperture flag zero.
- 3075599868480948992: centered compact source, nearby field structure and a nonuniform W3 background. W3 aperture flag zero.
- 2433664848010750848: centered compact source; the catalog flags aperture confusion despite no obvious resolved central split in these stretched panels. Keep the flag.
- 2984872253470024576: several nearby W1 sources, including sources in/near the outer sky region; diffuse or structured W3 surroundings. Catalog aperture confusion retained.
- 1742112230738093312: neighboring W1 source outside the small central aperture and structured W3 surroundings. Aperture flag zero.
- 2336863054027651456: centered compact source; other W3 sources toward the field edges. No obvious resolved central split; aperture flag zero. This does not explain or resolve the NIR fit discrepancy.
- 6669301637583655168: nearby field source below the target and a bright W3 source near the right edge. Aperture flag zero does not establish absence of faint blending.
- 2151835210082468992: several field sources and a bright W1/W3 object near the right edge; catalog central-aperture confusion retained.
- 3657301580397050240: neighboring sources in the wider field; catalog aperture confusion retained despite a visually compact central peak.

## Weakest NIR fit: 2336863054027651456

For the raw-parameter Rv=3.1 case, v11 fixed T=4980 K and fitted Av=0.175 with conditional J/H/Ks chi-square 6.463519. Observed-minus-model magnitude residuals are J=-0.018954, H=+0.050232, Ks=-0.027778. These use the existing v11 fit and are not a new fit or significance estimate.

Its 2MASS read flags are 212: J/Ks default magnitudes use profile-fitting to long Read_2 exposures; H uses 51 ms Read_1 aperture photometry, chosen when long exposures saturate. The H profile-fit chi-square refers to the long-exposure measurement and does not validate the short-read default magnitude. Native J/H/Ks Atlas panels show a centered compact target without an obvious resolved split; their central pixels are strongly peaked and the panels cannot independently validate the short-read H flux. The catalog lists nearest-neighbor proximity 24.4 arcsec.

Default H=8.753000, combined uncertainty=0.024100 mag; separately tabulated long-exposure standard-aperture H=8.714000, reported aperture uncertainty=0.018000 mag. Their 0.039000 mag difference is useful provenance context but is correlated, comes from different measurement paths, and is not grounds to replace H or lower the fit discrepancy. Read-method transitions, calibration, parameter/model errors and variability remain possible contributors; no cause has been established.

## Verification and replay

All 20 repository tests passed. The focused subset comprised 11 tests: three new fail-closed tests (reserved-role rejection, byte tamper rejection, wrong-band rejection even after a matching hash) and eight existing cohort/development tests. Diagnostics and summary replayed byte-identically with socket connections blocked. The archive includes the exact nine-star readiness inputs, development design/fit context, raw images and metadata, manifests, scripts and outputs. Native sky images are real catalog observations; synthetic pixels appear only in software tests.

From the archive root, install requirements-nir.txt, then run python -m scripts.development_image_audit replay. The frozen image design already exists: do not run freeze or acquire on the archived tree. python -m scripts.development_image_audit figures regenerates the panels. python -m scripts.development_nir_review verifies saved response hashes and regenerates the weakest-fit context/panel; all its expected native responses are present.

## Next checkpoint

Quantify counterpart/neighborhood contamination and specify a defensible predictive uncertainty model on development data. Keep flagged stars visible rather than selecting replacements based on residuals. Freeze eligibility, uncertainty treatment and evaluation criteria before scoring the reserved group. Nine development stars are too few to establish a tail calibration or reliable rare-anomaly detection rate. Production and Render remain unchanged; PR #7 stays draft/unmerged.

## Primary documentation

- AllWISE catalog aperture definitions and flags: https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html
- AllWISE Atlas photometry and uncertainty guidance: https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec4_3a.html
- Native AllWISE IBE path and cutout protocol: https://irsawebops2.ipac.caltech.edu/ibe/docs/wise/allwise/p3am_cdd/
- 2MASS all-sky default measurement provenance, read flags and limitations of PSF chi-square: https://www.ipac.caltech.edu/2mass/releases/allsky/doc/ancillary/pscformat.html
