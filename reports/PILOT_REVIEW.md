# Pilot sample review — 11 October 2026

The initial pull request passed its GitHub Actions offline import and all 25 tests.
Repository and API review found no additional defect requiring changes in this pass.

The diagnostics are computed from the frozen Gaia DR3 observations, with the source
checksum and database checksum recorded in `sample_diagnostics.json`. Run
`python -m scripts.sample_diagnostics` after installing `requirements-analysis.txt`.
The figure contains no inferred distances, anomaly scores or AI interpretations.

| Quantity | Entire sample | Provisional reference |
|---|---:|---:|
| Sources | 10,000 | 531 |
| Median observed G magnitude | 19.58 | 15.74 |
| Median observed BP − RP (mag) | 1.53 | 1.25 |
| Median parallax / standard error | 1.16 | 19.35 |

Medians exclude missing values; exact availability counts and percentiles are in
the JSON report. The full sample has 30 missing G magnitudes, 336 missing colors
and 1,383 missing parallax signal-to-noise ratios. It retains 2,040 negative
measured parallaxes. These are legitimate noisy measurements, not negative physical
distances. No reciprocal-parallax distance calculation is used.

Only 57 sources have the published VARIABLE classification; the other 9,943 have
NOT_AVAILABLE. That flag does **not** establish stable luminosity. The reference
screen is therefore provisional and will require independent variability checks.

The reference sources are systematically brighter and have much better astrometric
signal-to-noise. Direct comparison of full-sample and reference outlier rates would
confound observation quality with astrophysics. Before scientific anomaly testing,
create covariate-matched comparison cohorts with overlap checks, particularly in
magnitude, color, sky position, measurement quality and survey coverage. Do not
assign faint stars artificial controls outside the reference cohort's support.

The sky plot follows Galactic coordinates. Its color represents count per
projection bin, not density per equal solid angle. The three histograms normalize
against all available values in each cohort, including those outside display
limits; missing and clipped counts are displayed explicitly.

Next integration milestone: ingest a small, independently checked WISE crossmatch
with epoch-aware coordinates, alternatives, uncertainty and artifact flags before
attempting infrared excess interpretation. The protocol already requires these
checks; WISE photometry has not yet been imported.
