# Experiment 001B — AllWISE coverage and association pilot v1

## Scope and frozen selection
This is a data-readiness pilot, not an infrared-excess or technosignature test.
Select 100 of the existing 531 provisional Gaia references by SHA-256 of
`echolens-001b-v1:` plus exact source ID, breaking ties numerically. Do not select
on WISE brightness or detection. Freeze IDs, protocol hash, Gaia source hash and
search parameters before retrieving the targets' infrared observations.
Gaia source SHA-256:
`d193d7e144d5a7fc9f3d877a9323fc3c68ee2baf05b966d997392309a5248fb0`.

## Retrieval and associations
Query NASA/IPAC IRSA's `allwise_p3as_psd` catalog. Keep all 298 supplied columns
in original native FITS responses with paired VOTable field metadata, request
queries, endpoints, timestamps, checksums and TAP status. Query ten batches of
ten search cones, MAXREC=10001; reject truncation or ≥10000 returned nonempty rows.
Search 15 arcseconds around the Gaia position propagated to MJD 55400 (TT).
This radius is a retrieval envelope, not an identification claim.

Propagate Gaia ICRS position and proper motion on the unit sphere from its catalog
reference epoch, respecting pmra=mu_alpha*cos(dec). No inverse-parallax distance
or radial velocity is used; perspective acceleration and annual parallax are not
modeled. Retain the original Gaia errors and correlations through source provenance;
this first pilot does not calculate positional likelihoods from combined covariance.

For each infrared candidate, compare Gaia to AllWISE motion-fit ra_pm/dec_pm at
MJD 55400 when both are available. Otherwise use stationary ra/dec and propagate
Gaia to the W1 mean MJD, falling back to W2 mean MJD, then MJD 55400. Label all
stationary-position epoch choices as approximate: band mean dates are not exact
astrometric reference epochs for the combined stationary fit.

Keep every candidate within 15 arcseconds at its comparison epoch. Candidates
within 3 arcseconds are geometrically eligible. Zero eligible candidates remain
unmatched; multiple eligible candidates remain ambiguous. Do not choose the
nearest automatically. A sole eligible candidate is only a provisional association.
Flag other catalog neighbors within 6 arcseconds of the Gaia prediction, stationary
epoch approximations, motion-fit blend swaps and infrared source reuse across
different Gaia targets for review. A 15-arcsecond cone is not complete for arbitrary
high-motion objects, unresolved neighbors or catalog omissions.

## Photometry and quality
Keep W1–W4 profile-fit magnitudes, magnitude/flux uncertainties, fluxes and SNR,
contamination/confusion, photometric quality, moon contamination, saturation,
extendedness, blend counts and variability flags. `ph_qual=U` identifies a catalog
95% confidence upper limit in flux/brightness (the corresponding magnitude is a
lower bound), not a detection. `Z` is an uncertain measurement, not an upper limit.
Do not convert an upper limit to a measured excess. Missing values remain missing.

A band passes this operational screen only if: ph_qual=A; SNR>=10; finite
magnitude and positive magnitude/flux uncertainties; cc_flags='0'; moon_lev='0';
saturated-pixel fraction=0; reduced profile-fit chi-square<=2; ext_flg=0;
nb=1; na=0. Report failures explicitly without deleting observations.
Report conservative W1/W2-ready targets only for sole, motion-fit eligible
associations without neighbor/swap/reuse flags and with both bands passing.
These targets still need image inspection and covariance-aware association checks.

## Outputs and interpretation
Report all 100 target outcomes, candidate alternatives/separations, epoch choices,
band detections/limits/missingness and operational quality failures. Archive the
native observations, metadata and query manifests. Plot association outcomes and
per-band readiness. Offline replay must reproduce the derived result.
No stars are removed from the Gaia registry; outputs remain separate from measured
data. Do not fit a photosphere, score infrared excess, or assign artificial-origin
probabilities in this pilot. Negative coverage/quality results are retained.

Sources:
- AllWISE Source Catalog data model and flag definitions:
  https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html
- IRSA TAP access:
  https://irsawebops2.ipac.caltech.edu/docs/program_interface/TAP.html
