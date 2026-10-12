# EchoLens F01 transport reliability audit (October 2026)

Engineering only; no astronomy hypotheses or source data altered.

Verified: existing research/f01-selection-bias-20261011 branch contains scripts/f01_selection_bias.py (ESA Gaia DR3 UWS job; previous EXECUTING timeout) and scripts/f01_irsa_mirror.py (successful 20,000-star IRSA acquisition; exploratory eight IRSA AllWISE cone queries each previously made without retries). The historic IRSA mirror succeeded, and its output should not be mistaken for a failed acquisition.

The submitted patch concerning 'Gaia DR9' is inaccurate: Experiment 006B uses LAMOST DR9 LRS via ESA ESASky, not Gaia spectroscopy. Preserve LAMOST dates and real fiber offsets; Gaia RUWE is not a replacement.

New scripts/tap_reliability.py retries 408/429/500/502/503/504 and connection/timeout failures with capped exponential backoff, jitter and Retry-After; HTTP 400/401/403/404 are permanent failures. Tests inject fake HTTP responses without network access. The existing F01 AllWISE exploratory segment now uses this transport and logs provider, SHA-256, raw CSV, attempt history, and distinguishes no-match vs network failures.

Provider-specific query adapter is restricted to original IRSA AllWISE. An unvalidated CDS VizieR fallback is intentionally rejected; a CDS schema-specific adapter and source-equivalence assessment must be written and tested separately. Raw candidate lists, not TOP 1 or automatic nearest-source assertions, are preserved. No science scoring or all-sky query was added.

This patch does not change Render, Redis, Celery, main, the original F01 selection frame, or LAMOST 006B. The ESA UWS asynchronous job timeout is not resolved by HTTP retries alone. The study requires review before any live astronomy acquisition.
