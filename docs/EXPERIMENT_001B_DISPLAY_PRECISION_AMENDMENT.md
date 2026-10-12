# Experiment 001B derived-display numeric stability amendment

**Date:** 2026-10-11. **Scope:** only the *rounded, derived display value* `separation_arcsec` in `reports/experiment_001b/results.json`. The original 100 AllWISE FITS responses, Gaia measurements, observation uncertainties, selection manifest, quality screens, candidate geometry and all association decisions remain immutable.

## Reproducibility defect and evidence
GitHub Actions run [38146224800](https://github.com/gittenssexton/echolens-api/actions/runs/38146224800) and the separate diagnostic script found exactly one byte-level discrepancy after offline replay: `$.targets[86].candidates[0].separation_arcsec` changed from 0.177952 to 0.177953 arcsec (1 microarcsec). There was exactly one semantic JSON mismatch, and no evidence of changed native inputs or category/quality decisions. The native numeric computation can vary at low microarcsecond levels between floating-point/science-library builds.

## Frozen minimal correction
The numeric separation used to decide geometry remains **unrounded** and is compared with the same **3 arcsec eligibility** and **6/15 arcsec neighbor/retrieval** thresholds. The displayed derivation is rounded to **five** rather than six digits after the decimal point, corresponding to 0.00001 arcsec (10 microarcsec), far below the precision of the underlying AllWISE and LAMOST surveys. Do not round original catalog astrometry, magnitudes, uncertainties or source IDs.

Normalize the committed `separation_arcsec` fields to the nearest 0.00001 arcsec using an explicit half-up quantizer applied to the existing six-decimal display values (the calculations remain based on unrounded separation); never reselect candidate neighbors, adjust flags, change the association protocol, or invoke fresh network requests. Preserve the original six-decimal result in Git history. Then require full offline JSON byte-level reproducibility of both `results.json` and `observations.json`. If a different field or later threshold decision differs, treat as a new failure, never silently tolerate it.

This is an engineering serialization amendment **after** the originally registered scientific pilot, not a new scientific result or altered scientific cutoff.
