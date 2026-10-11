# Mixed Gaia–AllWISE–2MASS feasibility pilot v0.2

This implements the acquisition stage of the separately archived Experiment 001A infrared draft. The unique run name is `infrared-feasibility-v02` to distinguish it from the existing control-matching Experiment 001A and reference-only WISE Experiment 001B. No excess scoring or deployment is performed.

## Frozen design

Before target retrieval, select 40 provisional reference candidates, 40 remaining non-VARIABLE sources and 20 catalog VARIABLE sources. Sort each stratum by SHA-256 of `echolens-infrared-feasibility-v02:` plus its exact Gaia source-ID string, then numeric ID as tie-breaker. Each selected Gaia record is preserved in the selection manifest. The input is the primary frozen 10,000-source registry; Gaia raw SHA-256 `d193d7e144d5a7fc9f3d877a9323fc3c68ee2baf05b966d997392309a5248fb0`.

The reference-only 001B sample is a distinct engineering cohort. Overlap does not count as an independent replication. All selected sources in this run are development-exposed for this analysis version.

## Pre-acquisition implementation amendments

- Use 15-arcsec retrieval cones rather than the draft's proposed 10-arcsec envelope, matching its neighbor-review scale. This broadens retrieval, not acceptance; retain the 3-arcsec geometric eligibility radius.
- IRSA supports only one geometric constraint per query: run one request per target per survey with at most three concurrent requests. No WISE-brightness selection is applied.
- The feasibility calculation uses direction-only proper-motion propagation on the unit sphere, respecting `pmra = mu_alpha*cos(dec)`. It does not infer distance or model annual parallax/perspective acceleration. Missing motion remains explicitly flagged.
- AllWISE retrieval uses MJD 55400 TT; matching uses motion-fit positions at that epoch when supplied, otherwise the stationary position and approximate W1/W2 mean epoch. 2MASS retrieval uses approximate year 2000; matching uses each returned record's `jdate`. The retrieval envelope is not guaranteed complete for arbitrary motion, missing astrometry or catalog omissions.
- Covariance-qualified acceptance from the draft is deferred: geometric associations remain provisional even when unique. No false precision or confirmed object identity is asserted.
- WISE operational band screen: `ph_qual` A/B, SNR≥5, positive magnitude/flux errors, band's `cc_flags=0`, `ext_flg=0`, and zero reported saturated fraction. 2MASS screen: band's `ph_qual=A`, `cc_flg=0`, positive combined magnitude error. These readiness counts do not constitute the final frozen scientific quality rules. Report neighbors within 6 arcsec and reused catalog extractions as review flags.

## Original observations and replay

Retain all available columns in native FITS, with paired VOTable field metadata for each catalog. The existing validated snapshot parser rejects error/overflow status, checks metadata/native schema agreement and strips only independently verified trailing zero-filled transport padding. Per-response manifests preserve query, retrieval time, response hash, target selection hash and row count. Metadata manifests preserve their own acquisition provenance.

```
python -m scripts.import_gaia
python -m scripts.infrared_feasibility --select
python -m scripts.infrared_feasibility --fetch
python -m scripts.infrared_feasibility --replay
python -m pytest tests/test_infrared_feasibility.py -q
```

Selection refuses to overwrite an existing frozen manifest. Fetch resumes validated completed requests; no refresh is automatic. Offline replay verifies original bytes and reuses the archived metadata at its relocated path. Store the archived `reports/infrared_feasibility` tree in that location before replaying a downloaded package. The report is written without timestamps so repeated replay can be compared byte-for-byte. No Gaia registry rows or live service settings are modified.

## Interpretation

Report unmatched, ambiguous and sole geometric alternatives, per-band quality readiness, and joint W3/JHK readiness by stratum. Preserve non-detections and upper limits as their original flagged values. A unique counterpart or a band passing this screen still needs covariance checks, image inspection and model feasibility. No stellar photosphere, infrared residual, p-value, candidate rank, or technological-origin probability is computed.

Sources: [IRSA TAP](https://irsa.ipac.caltech.edu/docs/program_interface/TAP.html), [AllWISE fields](https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html), [2MASS PSC guide](https://irsa.ipac.caltech.edu/data/2MASS/docs/releases/allsky/doc/sec2_2a.html).
