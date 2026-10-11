# Experiment 001A — Gaia control-matching feasibility v1

## Registered question
Can the current provisional reference cohort supply distinct, covariate-matched
controls for at least 50 of 100 deterministically sampled non-reference sources?
The 50% threshold is an operational go/no-go criterion for this pilot, not an
astrophysical null hypothesis or a statistical significance threshold. This
experiment measures feasibility; it does not search for technology.

## Frozen inputs and target selection
Use PR #2's frozen Gaia DR3 snapshot (10,000 actual observed catalog sources),
raw SHA-256 `d193d7e144d5a7fc9f3d877a9323fc3c68ee2baf05b966d997392309a5248fb0`.
Controls pass the existing `is_reference` screen, unchanged. Targets are all
remaining sources, ordered by SHA-256 of `echolens-001a-v1:` plus exact source ID;
take the first 100. A tie is broken by numeric source ID. Store all target IDs,
source digest, protocol digest, algorithm version and thresholds before executing
matching. No target is selected by an anomaly rank or by having complete data.

## Fixed matching rules
Require finite G magnitude, BP−RP color, Galactic latitude, positive parallax
signal-to-noise and positive RUWE for both target and control. A candidate pair
must satisfy all five tolerances:

| Covariate | Maximum difference |
|---|---|
| Observed G magnitude | 0.5 mag |
| Observed BP−RP color | 0.25 mag |
| Absolute Galactic latitude | 10 degrees |
| Parallax / standard error | Factor of 2 |
| RUWE | Factor of 2 |

Use a deterministic maximum-cardinality bipartite matching, one control per target,
no control reuse. Order eligible choices by Euclidean distance in tolerance-scaled
covariates, then numeric control ID. This does not claim a globally minimum-cost
assignment. Negative/missing parallaxes remain in the registry; a nonpositive or
missing parallax SNR has no match under this explicitly positive-SNR control rule.
No inverse-parallax distance or inferred stellar parameter is used.

## Primary output and reporting
Report matched targets / 100 and whether it meets 50%. Preserve every target,
including unmatchable ones. Separately report missing/invalid matching covariates,
zero eligible controls, and targets unassigned despite eligible controls. Record
all eligible alternatives, assigned pair covariates/differences and cumulative
eligibility after each tolerance. Publish sky/brightness/color diagnostics and
negative findings. Do not alter thresholds after seeing results; a revised pilot
must receive a new protocol version and retain the first result.

## Limits and interpretation
These are provisional catalog controls, not confirmed ordinary or lifeless stars.
NOT_AVAILABLE variability does not establish constancy. Galactic latitude is a
coarse sky proxy, not a local-density/extinction match. The five covariates do not
match metallicity, gravity, temperature, full covariance, extinction, survey
coverage, unresolved binaries or observation epoch. Even a passing pilot cannot
authorize a scientific anomaly comparison without those further checks.

The fraction applies only to these 100 targets and this frozen, classification-
selected catalog snapshot. No general stellar-population prevalence, FDR,
technosignature confidence or causal inference is calculated. All products are
reproducible derived diagnostics, stored separately from measured registry data.
