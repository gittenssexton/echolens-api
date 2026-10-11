# EchoLens Experiment 008 — independently measured stellar-reference cohort and deterministic holdout feasibility

**Protocol v1 frozen 2026-10-11, before running the new cohort screens or matching.** Study type: observational selection/feasibility using already-acquired real catalogs. **No technosignature search, astrophysical null test, or claim that screened stars are confirmed ordinary.** Everything runs on a separate branch, no main/Render change.

## Fixed source universe and evidence levels

Exactly the original **250 real LAMOST DR9 spectra** independently obtained through Huang et al. 2024 / VizieR in Experiment 003. Retain every spectrum including all failures, original units, uncertainties, and exact obsid/Gaia DR3 IDs as decimal strings. Require the **frozen** original SHA-256 of:
- 003 LAMOST-derived `results.json`: `efc4f3eaf5f5e1df8b60aa1897ffd93d44c3b05fe69318b27d3769fddb342e51`.
- 003G Gaia DR3 audit `results.json`: `d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748`.
- 006B ESA DR9 mirror `results.json`: `73b2dbf80ff591d42386c4149dcea1e0ca2225569728dd94c8efacb7609b4fa7`.
- 007 original analysis result and two native ESA DR8/Gaia conflict responses from successful [run 38157271013](https://github.com/gittenssexton/echolens-api/actions/runs/38157271013) (archive preserved in [Echo Lens Drive](https://drive.google.com/file/d/1jX6s-bCJflIyiffKpf7qHyC9iVbWm7z2/view?usp=drivesdk)). Validate that nine ESA DR9-missing obsids are **all present in ESA DR8 LRS** and that 007 still reports both disputed Gaia IDs.

**Primary tier A — cross-catalog-concordant reference *candidates*, NOT certified source identities:** original VizieR/Huang published Gaia ID agrees exactly with an ESA DR9 LRS `gaia_source_id`; exact original Gaia DR3 ID exists; original LAMOST `obsid` matches. This intentionally excludes nine ESA DR9-missing records even though ESA DR8 independently records their obsids, and excludes two conflicting Gaia IDs plus one ESA missing-id sentinel. They remain explicit secondary provenance tiers `DR8_only`, `competing_Gaia_ID`, `ESA_missing_Gaia_ID`.

Other classification gates applied **in registered order**, preserving multiple failure reasons:
1. Instrument and observation: ESA DR9 `offsets=0` and nonmissing flag, reported MJD consistent with `obsdate` (as in 006B); all spectroscopic per-source quality labels (`spectroscopic_label_ready=True` from frozen 003).
2. Gaia record reliability: real positive `parallax/parallax_error >= 10`, finite observed BP−RP, finite G, `ruwe < 1.4`, `duplicated_source=False`, `non_single_star=0`; complete finite Gaia pmra, pmdec, their nonnegative uncertainties; `phot_variable_flag != 'VARIABLE'` (NOT_AVAILABLE means *unknown*, not stable). If any of these fields are absent, record a specific missing-quality failure; do not impute.
3. Dwarf/parameter and activity *measurement coverage*: independently derived LAMOST spectroscopic `4800 <= Teff <= 6800 K`, `3.9 <= logg <= 4.7 dex`, `-0.8 <= [Fe/H] <= +0.45 dex`, with strictly positive published per-parameter formal uncertainties. The **measured** Ca II 8542 activity R-index and reported uncertainty must both be finite, and uncertainty >0. Do NOT use Ca II to assert astrophysically quiet or to define the reference group after observing results. No emission-line classification claim is possible from this alone.
4. **Catalog-to-target astrometric diagnostic:** using Gaia DR3 J2016.0 position and proper motion and the actual ESA DR9 `mjd`, calculate tangent-plane PM-corrected distance to **input target `ra,dec`** (not the deliberately displaced fiber). Require <=1.0 arcsec, not 0.5 arcsec. This approximate geometry omits parallax/perspective, full covariance, fiber pointing uncertainties; therefore passing is *provisional* and is NOT full identity certification. The >1" failure threshold is operational, not statistically calibrated.

Do not silently remove natural positives, highly active or dusty stars: these measurements are not available with scientifically calibrated quietness labels. State explicitly that survey selection (FGK, high optical SNR and bright G) defines the **restricted** applicability domain.

## Frozen deterministic study and threshold

If **>=80** sources pass all candidate gates, form a *withheld* set of exactly 40 target spectra by sorting eligible `obsid` on `SHA256("echolens-008-v1:"+obsid)`, numeric `obsid` as tiebreak. The remaining passers are potential non-reused controls. Otherwise report all gates and `not_executable_insufficient_candidates` without selecting substitutes.

Match each target to distinct controls with these prespecified observed/inferred covariate tolerances, all simultaneously:
- |ΔGaia G| <= **0.75 mag**
- |ΔGaia BP−RP| <= **0.30 mag**
- |Δspectroscopic Teff| <= **350 K**
- |Δspectroscopic logg| <= **0.50 dex**
- |Δspectroscopic [Fe/H]| <= **0.30 dex**
- max(parallax SNRs)/min(parallax SNRs) <= **3**

Eligible edges sort by sum of squared tolerance-normalized differences, followed by numeric control obsid. Construct deterministic maximum-cardinality one-to-one bipartite assignment via augmenting paths in sorted target order. Report all candidate edges, assigned IDs, calibrated differences, counts and nonmatches, with no reuse or removal. The prespecified *operational* pass is **>=25 distinct matched targets of 40**; if the criteria fail, preserve the failure unchanged and propose a separate future study, never relax thresholds retroactively.

## Required scientific output and missing-evidence audit
- Per-original-spectrum audit for all 250: raw obsid/ID references, ESA DR9/DR8 provenance tier, every failed gate, observed vs inferred fields (measurement values and formal uncertainties), astrometric distance, instrumental-offset flags and observation MJD, Gaia variance/non-single-star markers.
- Flow from 250 -> concordant -> instrument/date -> Gaia reliable -> spectroscopic/coverage -> astrometric candidate -> withheld matching result, including overlap and attrition; number of candidates and *matched* stars clearly separated.
- Summary of Gaia G/Teff/logg/[Fe/H], parallax SNR and Ca II 8542 (no invented spectra or activity classifications), and brightness comparison with frozen initial 10,000 Gaia pilot (median G≈19.58).
- **Missing survey-coverage flag** for every source: no AllWISE/2MASS/GALEX matched coverage was obtained for these independent 250; record `wise_verified=False, twomass_verified=False, extinction_verified=False, spectral_activity_class_verified=False, full_covariance_crossmatch_verified=False`. These are *unknown/not verified*, not negative survey detections or biological evidence. **Final fully verified science-ready ordinary control cohort size = 0**, pending additional crossmatch, astrophysical calibration and survey coverage. If a larger provisional cohort passes, it is a **candidate** set only.
- Deterministic `results.json` and a concise README/report with all preregistered denominators; compare two independent offline replays byte-for-byte; store original input hashes, protocol hash and immutable source references.

## Limitations and no false discovery
Cross-survey agreement may arise from common source-matching assumptions; even exact ESA ID concordance does not independently certify spectra. `phot_variable_flag=NOT_AVAILABLE` is **not** proof of nonvariability. High optical SNR and spectroscopic formal errors do not cover model systematics, sky extinction, crowding, binarity, active stars, dust, resolution/covariance or X-ray/radio/IR background. Do not infer null evidence for extraterrestrial life, treat all nonmatching stars as anomalies, or run WISE excess significance here.

**No network astronomy download needed for this phase**: run solely from preserved real observations. No serving registry/Render/main modifications, no source-value overwrites, no merging before scientific review.
