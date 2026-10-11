# EchoLens Experiment 002A — executed feasibility report

**Date:** 2026-10-11 (UTC)  
**Status:** Conditional cohort matching feasibility criterion met; **no scientific anomaly analysis**  
**Input:** Gaia DR3 real observations, frozen IRSA FITS sample of 10,000 sources  
**Uncompressed archive SHA-256:** `d193d7e144d5a7fc9f3d877a9323fc3c68ee2baf05b966d997392309a5248fb0`  
**Registered protocol:** [EXPERIMENT_002A.md](../../docs/EXPERIMENT_002A.md), committed *before* the analysis script in commit `5512765311de480696ce3fd901a3387d5af16044`.

## Result

| Preregistered measure | Observed |
| --- | ---: |
| Source catalog size | 10,000 |
| Pre-existing provisional reference-screen pool | 531 |
| Hash-selected held-out high-quality target stars | 100 |
| Remaining provisional controls (without reuse) | 431 |
| Targets matched to a distinct eligible control | **95** |
| No eligible control | 5 |
| Missing/nonpositive covariates | 0 |
| Eligible controls lost to competition | 0 |
| Operational criterion | At least 50/100 |
| Criterion met | **Yes (95/100)** |

**Cumulative support:** With the fixed five-dimensional tolerances, 100 targets have an eligible control after the G-magnitude cut; 100 after the color cut; 97 after the absolute Galactic latitude cut; 95 after the parallax-SNR cut; 95 after RUWE. Matching uses the same squared tolerance-normalized distance order, one-to-one maximum-cardinality assignment and exact cut values as Experiment 001A. No rules were relaxed after the result.

## Scientific interpretation / how NOT to use this result

This result shows that, **conditional on an intentionally bright/high-SNR Gaia selection**, internally comparable reference-screen sources can be withheld and paired without control reuse. It does not validate the clean screen's astrophysical labels; `NOT_AVAILABLE` variability does not prove stable luminosity. It does not validate comparisons to the general 10,000-source catalog.

**Experiment 001A remains a failed 3/100 feasibility outcome**, using non-reference targets. The 95/100 figure comes from a *different target population* deliberately restricted to the high-quality screen; the two percentages are not an improvement in a fixed general-population matching rate. The result does not address dust, extinction, metallicity, surface gravity, local crowding, full covariance, unresolved companions, time-series behavior or cross-survey coverage. No p-value, technosignature score, astrophysical prevalence, or claim of non-technological life is warranted.

## Reproduction and provenance

```sh
python -m scripts.import_gaia
python -m scripts.control_overlap_002a --output /tmp/echolens-002a-first
python -m scripts.control_overlap_002a --output /tmp/echolens-002a-second
cmp /tmp/echolens-002a-first/results.json /tmp/echolens-002a-second/results.json
python -m pytest -q
```

GitHub Actions [workflow run 38144476622](https://github.com/gittenssexton/echolens-api/actions/runs/38144476622) passed: the full test suite including new tests, the earlier registered 001A replay, two 002A runs and byte-for-byte equality of their `results.json` files. Its artifact [echolens-control-overlap-002a](https://github.com/gittenssexton/echolens-api/actions/runs/38144476622/artifacts/11704262702) contains all 100 source IDs/outcomes, 431 control IDs, potential matches, chosen pairs, scaled differences, distributions and frozen provenance. **The Actions artifact expires 2026-11-10; archive it durably before that date.** The executable procedure and frozen catalog permit re-creation after expiration.

All observations, database schema, API endpoints, the `main` branch, and Render service are unchanged. This report is a derived experiment log, not a catalog measurement.

## Next scientific review gate

1. Inspect pair-by-pair distributions and reject residual poor-balance pairs *only by writing a new prospective protocol*, never by altering 002A's published counts.
2. Build a new, independently characterized comparison set with additional astrophysical covariates and survey-coverage checks; use explicitly matched support, not the entire broad Gaia pilot.
3. Resolve Experiment 001B WISE reproducibility failures before using its quality-qualified infrared associations for science.
4. Pre-register photosphere-model residual definitions, null calibration, systematic errors and independent confirmation before ranking any stellar electromagnetic outliers.
