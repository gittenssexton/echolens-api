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
