# EchoLens Experiment 002A — clean-reference overlap feasibility, preregistration v1

## Registered question (engineering feasibility; NOT an anomaly search)
Can 100 withheld high-quality Gaia DR3 reference-screen sources each be compared with a **distinct** source from the remaining high-quality reference pool under the original Experiment 001A matching tolerances? The primary preregistered go/no-go rule is **at least 50/100 distinct matched targets**. This is a practical feasibility threshold, not an astrophysical null, significance threshold, evidence for technosignatures, or proof of control suitability.

Experiment 001A (3/100 matches for non-reference targets) remains immutable. This deliberately conditional 002A cohort is a NEW design that tests matching **within** the bright/high-SNR reference population; it must never be used to claim matching success for all 10,000 sources or to rehabilitate the failed 001A result. All results remain exploratory/development-exposed.

## Frozen data and deterministic selection
Use only the original, real Gaia DR3 IRSA frozen 10,000-source snapshot (uncompressed raw SHA-256 `d193d7e144d5a7fc9f3d877a9323fc3c68ee2baf05b966d997392309a5248fb0`) and `is_reference` from `scripts/import_gaia.py` on the 001A branch **without changing any screening rule**. The current screen yields 531 provisional high-quality sources.

Before computing any matches:
1. Verify the original raw SHA-256, manifest and `validate(rows, 10000)`.
2. Form the screened pool and sort by (`SHA256("echolens-002a-v1:" + exact source_id)`, numeric source_id).
3. Reserve the first 100 sources as held-out targets. Use the remaining screened sources as comparison candidates. There is no reuse or intersection.
4. Log all 100 selected target IDs, control IDs, input checksum and protocol checksum with the derived output.

No candidates are selected by a score, WISE photometry, anomaly status or eventual matching success. Null and negative parallaxes remain in the original registry even though the quality-screened 002A population excludes them.

## Frozen matching algorithm and threshold
Reuse `covariates`, `differences` and `maximum_matching` from `scripts/control_matching.py` (001A). Require finite observed G, BP−RP, absolute Galactic latitude, positive parallax SNR and positive RUWE. Match iff ALL inequalities hold:
- |ΔG| <= 0.5 magnitude
- |Δ(BP−RP)| <= 0.25 magnitude
- |Δ|Galactic latitude|| <= 10 degrees
- max(parallax SNRs)/min(parallax SNRs) <= 2
- max(RUWEs)/min(RUWEs) <= 2

Sort eligible controls by squared tolerance-scaled distance, then numeric Gaia source ID. Use deterministic maximum-cardinality bipartite assignment (without replacement); do not re-optimize the rule after seeing results. A passing result means only that this **restricted** provisional clean-population comparison can produce >=50 pairs, not that it is scientifically unbiased.

## Outputs and bias reporting
Write a deterministic `results.json` with source and protocol SHA-256, selection salt, precise input IDs, candidate eligibility lists, target and control covariates, assigned IDs, per-pair normalized differences, stage-wise overlap counts, status reasons and the primary pass/fail criterion. Re-running against the frozen raw catalog must yield byte-identical JSON. Preserve all 100 results including failures. A result must not be merged back into measurements or AI interpretations.

Report brightness/color/parallax-SNR summary differences between held-out sources and the 10,000-source population. State explicitly that reference cuts intentionally create a brighter, high-SNR subpopulation and that the final inference domain is restricted to the matched support. No candidate scores, p-values, false-discovery claims or technology probabilities are allowed.

## What this experiment does NOT establish
The 531-screen is not independent confirmation of ordinary stellar physics; `phot_variable_flag=NOT_AVAILABLE` is not a stability certification. Five matching covariates omit extinction, surface gravity, metallicity, detailed crowding, full covariance, known binaries, time-domain behavior and WISE/2MASS coverage. The held-out source identities do not remove model-selection bias because the overall clean-screen and tolerances were defined after past work. Independent labels and a new observational sample are required before confirmatory tests. WISE pilot 001B's associations and photometric quality outcomes are not incorporated in this experiment.

Relevant Gaia definitions: https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_main_source_catalogue/ssec_dm_gaia_source.html
