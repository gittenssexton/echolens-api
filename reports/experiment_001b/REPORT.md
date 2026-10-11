# Experiment 001B results

The frozen 100-star Gaia reference subset yielded 93 provisional unique
AllWISE associations, 1 ambiguous associations, and
6 targets without an eligible candidate.
34 targets passed the conservative W1/W2 screen for subsequent image review.
These are data-readiness outcomes, not infrared excesses or technosignature detections.

Retrieved 151 distinct real AllWISE catalog sources with all
298 fields preserved. Native FITS and original field metadata retain
measurement uncertainties, missingness, quality flags and source provenance.
The selection was frozen before retrieval. The separately committed transport
amendment replaced unsupported multi-cone queries with individual cone requests.

## Per-band outcomes

Counts below use only the 93 provisional unique associations. Quality
passes and flux upper limits are distinct categories; other failed or missing
measurements remain in the observations and results.

| Band | Quality passes | 95% flux upper limits |
| --- | ---: | ---: |
| W1 | 41 | 0 |
| W2 | 39 | 0 |
| W3 | 7 | 57 |
| W4 | 0 | 85 |

## Review flags and quality failures

Flags can overlap: approximate_stationary_epoch: 3, motion_fit_blend_swap: 1, nearby_infrared_neighbor: 1.

W1: active_deblending: 8, blend_count: 11, contamination: 17, extendedness: 10, fit_chi_square: 23, moon_contamination: 17, photometric_quality: 1, saturation: 7, snr: 1.

W2: active_deblending: 8, blend_count: 11, contamination: 22, extendedness: 10, fit_chi_square: 6, moon_contamination: 21, photometric_quality: 1, saturation: 4, snr: 1.

W3: active_deblending: 8, blend_count: 11, contamination: 8, extendedness: 10, magnitude_and_errors: 57, moon_contamination: 30, photometric_quality: 81, snr: 81.

W4: active_deblending: 8, blend_count: 11, contamination: 6, extendedness: 10, magnitude_and_errors: 85, moon_contamination: 31, photometric_quality: 93, saturation: 2, snr: 93.

## Limits and next step

All associations are provisional. Gaia motion propagation excludes perspective
acceleration and annual parallax, and this pilot does not combine astrometric
covariances or estimate match probabilities. Stationary AllWISE epoch fallbacks
are approximate. Catalog blending and the finite retrieval cone can hide sources.
The Gaia reference subset is selected for measurement quality and is not a
population-representative or independently validated astrophysical control group.

Review images and positional covariance for the passing targets, then use optical,
near-infrared and WISE photometry in a photosphere model with extinction and
uncertainties before testing excess. Dust, companions and background objects
remain ordinary explanations to investigate. Preserve this pilot unchanged.

## Reproduction and provenance

```
python -m scripts.wise_pilot replay --output /tmp/wise-replay
cmp reports/experiment_001b/results.json /tmp/wise-replay/results.json
cmp reports/experiment_001b/observations.json /tmp/wise-replay/observations.json
python -m scripts.wise_pilot_report
```

Replay uses only committed snapshots; do not run `fetch` to reproduce this result.
The committed `data/wise_001b.tar.gz` contains the native responses and
`wise_001b/manifest.json` with all queries, timestamps, raw checksums and
the transport amendment hash; `selection.json` for exact Gaia IDs and the protocol
hash; and `observations.json` for metadata, original measurements and units.
Derived associations and screens are in `results.json`, separate from observations.

Data: NASA/IPAC IRSA AllWISE Source Catalog (`allwise_p3as_psd`), WISE
(UCLA/JPL-Caltech) and NEOWISE (JPL-Caltech), funded by NASA. Gaia mission data
processed by ESA's Gaia Data Processing and Analysis Consortium (DPAC).

Catalog definitions: https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html

IRSA TAP: https://irsa.ipac.caltech.edu/docs/program_interface/TAP.html
