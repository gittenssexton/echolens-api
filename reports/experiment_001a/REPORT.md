# Experiment 001A: first control-matching result

A 100-target feasibility experiment has been executed on actual frozen Gaia DR3
observations. Its protocol, source IDs and rules were committed before matching:
https://github.com/gittenssexton/echolens-api/commit/0b824c2cb5952143069867e186b2aa2c15cd2f74

## Result

| Outcome | Targets |
|---|---:|
| Assigned a distinct eligible control | 3 |
| Missing or nonpositive matching inputs | 34 |
| Usable inputs but no eligible control | 63 |
| Eligible control lost through competition | 0 |
| Total | 100 |

The predeclared operational criterion of at least 50 matched targets was not met.
No tolerance was changed after seeing this result. This is a negative feasibility
finding, not an anomaly detection or evidence of artificial activity.

Of the 66 targets with usable matching inputs, 21 had a reference satisfying the
brightness tolerance. Adding color left 12; absolute Galactic latitude left 11;
parallax signal-to-noise left 3; RUWE left 3. The maximum-cardinality assignment
used three different controls from the 531-source provisional reference pool.

## Implication

The present high-quality reference pool cannot support broad comparisons for
these targets. Restricting analysis to its overlap region or designing a broader,
independently characterized reference cohort requires a new protocol version.
Missing/nonpositive parallax signal-to-noise does not make a star abnormal; it
makes it unmatched under this particular positive-SNR control rule.

Controls remain provisional. A Gaia variability flag of NOT_AVAILABLE does not
establish constancy. These covariates do not fully match extinction, metallicity,
gravity, local crowding, binaries, epoch or later infrared/spectral coverage.
Matched targets are not certified suitable for technosignature hypothesis tests.

## Reproduce

Install requirements-analysis.txt, then run:

```sh
python -m scripts.control_matching --plot
```

The original catalog is checksum-verified before analysis. selection.json freezes
100 target and 531 reference IDs; results.json stores all 100 outcomes, eligible
alternatives, matching covariates, pair differences and provenance hashes.
An independent second offline execution reproduced identical JSON bytes.
The figure summarizes derived feasibility results; measured data were not changed.
