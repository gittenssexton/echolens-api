# WD counterpart engineering pilot CP001

Design frozen before Gaia requests; see reports/wd_counterpart_design_20261013.json.
Select 10 unique reported Gaia IDs from the verified DR9 WD snapshot: valid
native positions, ISO observation date, no declared intentional fiber offset,
lowest eligible numeric obsid per ID, then fixed hash ranking. This samples the
eligible WD archive without selecting Gaia quality or match outcomes.

Retrieve exact reported IDs and Gaia neighbors within 60 arcsec of both input
and fiber positions at the Gaia reference epoch (cap 5,000 rows; overflow fails).
Preserve raw VOTables, requests, retrieval times, fields/units/nulls, astrometric
errors and correlations. Do not substitute a nearby ID for a missing reported ID.

Apply constant tangent-vector proper motion to obsdate; retain unpropagated
separation, input/fiber difference and propagated candidate separations. Missing
motion is unresolved, never zero. Propagate Gaia-only tangent covariance and
label it separately from unavailable LAMOST centroid/epoch uncertainties.

The 3 arcsec fiber tolerance is an engineering sensitivity screen, not a
confidence interval. Classify missing IDs, missing astrometry, disagreement,
multiple candidates and conditional single-position support explicitly. J2000
equinox does not establish a measured-position epoch. Fiber pointing is not a
stellar centroid. Parallax, perspective acceleration, LAMOST position errors,
Gaia detection incompleteness and source confusion are not fully modeled.
No case is marked physically certified or selected as an ordinary control.
This pilot is not an infrared/spectral anomaly experiment or population estimate.
Main, Render and the serving database are untouched.

## Completed engineering result

All ten exact reported Gaia DR3 IDs returned; the combined bounded neighbor
request returned 167 rows with successful TAP status. All ten cases have a
single positional-support candidate inside 3 arcsec under the PM-only model.
Propagated fiber separations range 0.0194–1.1524 arcsec. This is conditional
support, not physical counterpart certification: zero cases are certified.
Raw requests/responses, native error/correlation fields and derived outputs
are retained. Offline replay with socket connections blocked reproduced the
results exactly. Frozen design commit: f855187a4273508b9f77f600ece8e1b1ddf6e73f.

Replay: `python -m scripts.wd_counterpart_pilot design.json raw-directory`.
Acquisition requires explicit `--acquire` and a new destination directory.
Evidence: https://drive.google.com/drive/folders/1_uhcsuKI-r3SSOBLhB5QKGLJ7ft3tNO5
The next scientific gate remains positional-epoch/centroid uncertainty review,
including original spectral metadata and image-based ambiguity assessment.
No WISE excess scoring or ordinary-control certification was performed.
