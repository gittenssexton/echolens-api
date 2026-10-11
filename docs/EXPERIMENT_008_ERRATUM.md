# Experiment 008 engineering erratum — native Gaia duplicated_source boolean encoding

**2026-10-11; registered AFTER first CI run but BEFORE re-execution.** Historical initial run [38158547605](https://github.com/gittenssexton/echolens-api/actions/runs/38158547605) completed 83 tests and two byte-identical analytical replays, but reported **0/250 quality candidates** and **0 matched targets** because it interpreted Gaia's published **integer** `duplicated_source` value `0` as a failed Python singleton `False` check.

Original IRSA/Gaia DR3 records in this frozen 250-star sample encode the existing `duplicated_source` field as **244 integer zeros** and **6 integer ones**. In Python `0 is False` is false, so the original check `if duplicated_source is not False` incorrectly marked **all 250** as duplicates regardless of the actual catalog values. This is **an ingestion type/serialization mistake**, not a scientific hypothesis result, cutpoint failure or newly observed stellar property.

## Correction
- Interpret the exact existing Gaia binary duplicate flag as a *semantic boolean*: **accept 0/False**, reject **1/True**, reject **null/unrecognized**. No threshold, cohort selection salt, 250-source identity, Gaia raw observation, original VOTable, matched covariate tolerance, source uncertainty, comparison rule, or status semantics change.
- Add a regression fixture for numeric 0 (must pass this gate) and numeric 1 (must fail).
- Rebuild and rerun the same frozen Experiment 008 pipeline with previously committed criteria. Report both the initial invalidated engineering output and corrected result separately; do not silently rewrite the first-run artifact or present the initial 0 as a meaningful astrophysical failure.
- The first-run artifact is `echolens-stellar-reference-008` from run 38158547605, artifact `11709293196`, retaining all 250 per-source rejection reasons and raw values. Compare after re-run.

## Scientific integrity
This correction **does not relax** the registered exclusion of actual duplicated Gaia stars and cannot be used to claim any star is stable, quiet, unblended, instrument-free or independently source-verified. All further matching outcomes, including a negative/null result, must be retained unchanged after this data-type correction.
