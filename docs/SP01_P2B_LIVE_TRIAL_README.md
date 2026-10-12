# SP01-P2B bounded real-catalog acquisition attempt

2026-10-12, development-only, no deployment or anomaly claims.

**Purpose:** Run the previously frozen `docs/SP01_P2B_PROTOCOL.md` selection against original real GALAH DR4 `galah_dr4.main_star` TAP responses plus independent Escorza et al. (2026) s-process-rich Gaia identifiers (`J/A+A/712/A111/catalog` in VizieR). Keep original downloaded bytes and exact queries/hashes. A successful cohort is 40 ordinary (20 calibration/20 holdout) plus 10 independent, published positive examples; if any stratum is short or public archive errors occur, **no cohort is claimed**. This is a feasibility sample from bounded TAP selections, not a statistically representative subset of GALAH.

**Run:** GitHub Actions `.github/workflows/sp01-p2b-acquire.yml` on research branch only. The workflow makes bounded POST TAP requests (four TOP 180 normal strata, up to 1059 independent labels, up to 150 targeted positive IDs) and archives original CSV responses, provenance and either frozen manifest or failure.json for 30 days. It never fetches spectra, changes the main branch, or modifies Render.

**Scientific caveat:** Escorza's 1059 s-process-rich binary candidates are *natural positives* for spectral-line validation, not confirmed manifestations of the same process as the ordinary dwarf, and may contain varied evolutionary states. This distinction is preserved in labels.

Primary catalog: https://www.galah-survey.org/dr4/the_catalogues/
Independent positives: https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=J%2FA%2BA%2F712%2FA111
