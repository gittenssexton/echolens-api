# EchoLens Experiment 008 — real stellar-reference candidate cohort and fixed matched holdout

**Executed and verified 2026-10-11.** **Status: preregistered restricted-cohort matching feasibility PASSED; astrophysical control certification NOT completed.**

## Research question and design

Can real LAMOST DR9 independently inferred stellar parameters, quality-controlled Gaia DR3 measurements, observation-date/cross-identification provenance and instrumental-fiber metadata produce a screened set of **provisional** bright FGK stellar-reference candidates, then successfully match **40 hash-withheld targets** to distinct controls on six pre-registered observed/inferred covariates?

Original [registered protocol](../../docs/EXPERIMENT_008.md) commit `02fc7c3145e42b2b60d0916aa59d04a736626118`, recorded **before** real Experiment 008 cohort screening or matching. No scientific cutoffs, holdout salt, tolerances, exclusion semantics or real Gaia/LAMOST observations were changed after examination of outcomes. A documented [Gaia boolean transport engineering erratum](../../docs/EXPERIMENT_008_ERRATUM.md) explains and preserves the initial invalidated run separately.

Input: **250 genuine LAMOST DR9 Huang+ 2024 published spectra**, Gaia DR3 astrometric/photometric source records, ESA ESASky LAMOST DR9 LRS date/input/fiber records, ESA DR8 LRS coverage information, original 007 Gaia candidate-ID alternatives, all retrieved in previously frozen real-observation experiments. All input provenance and SHA-256 hashes are in `results.json`, using successful historic GitHub Actions run artifacts 38146071576, 38146667656, 38152809325 and 38157271013. No astronomy catalog network queries made during this phase.

## Preregistered screening — exact counts

| Successive quality gate (each gate cumulative) | Real spectra retained | Excluded at this stage |
| --- | ---: | ---: |
| Original published LAMOST spectra | **250** | — |
| Published ESA DR9 and original Huang+ Gaia ID agree | **238** | 12 |
| No recorded fiber offset; usable observation date and spectroscopy | **230** | 8 |
| Gaia DR3 astrometric and photometric quality, nonvariable catalog flag, no known binary/duplicate flag | **179** | 51 |
| LAMOST inferred dwarf-like Teff/logg/FeH ranges, real uncertainties and Ca II 8542 measurement coverage | **175** | 4 |
| Approximate Gaia PM-propagated position within 1" of *input target* | **172** | 3 |

All 250 original stars are retained in the audit, including **9 ESA DR8-only**, **2 conflicting ESA/Huang Gaia IDs**, **1 missing ESA Gaia ID**, and **8 deliberately offset spectra among 238 concordant**. The previously explained 4.89" LAMOST instrument-offset star is *not* reused as a provisional clean reference.

The 250-star reason histogram includes **45 Gaia RUWE missing/high**, **11 low/missing parallax SNR**, **8 catalogued VARIABLE**, **6 catalogued duplicate**, **7 Gaia non-single-star present/missing**, **9 total published fiber offsets**, **3 out-of-range logg**, **3 out-of-range FeH**, and **16 position offsets >1"/not assessable**. These are **non-exclusive** per-source reason counts, not disjoint losses from the sequence above. Full source-level evidence and both measured/inferred parameter errors are retained.

The initial **invalidated engineering run 38158547605** applied a Python singleton-`False` check to Gaia's published `duplicated_source` native **integer 0/1** field, mistakenly rejecting all 250; original frozen archive has **244 numeric 0** and **6 numeric 1**. The engineering [erratum](../../docs/EXPERIMENT_008_ERRATUM.md) changed only transport interpretation (`0 == False`, `1 == True`), preserving the prespecified *exclude truly duplicated stars* rule, raw observations and all cutpoints. The first invalidated output is archived separately in [Echo Lens Drive](https://drive.google.com/file/d/1O2EVtt8HH89WC5qTGWsmZz6ehc3a3V9p/view?usp=drivesdk), never silently overwritten.

## Fixed withheld-target matched-comparison feasibility

| Frozen measure | Result |
| --- | ---: |
| Quality-screened **candidate** spectra | **172** |
| Hash-selected withheld target spectra | **40** |
| Distinct available remaining controls | **132** |
| Targets matched to distinct controls | **37 / 40** |
| Match rate | **92.5%** |
| Registered operational pass threshold | 25 / 40 |
| Operational criterion satisfied | **YES** |
| Unmatched: no eligible control | 2 |
| Unmatched: lost due to one-to-one control competition | 1 |
| Control identity reuse | **0** |

There was **no tuning after observing this result**: `SHA256("echolens-008-v1:"+obsid)` predetermined 40 targets; all eligible controls were from the 132 others. Conditions simultaneously: ΔGaia G≤0.75 mag, ΔBP−RP≤0.30 mag, ΔLAMOST spectroscopic Teff≤350 K, Δlogg≤0.50 dex, Δ[Fe/H]≤0.30 dex, and positive Gaia parallax-SNR ratio≤3. Deterministic maximum-cardinality one-to-one matching assigned controls to 37 targets; the original 40 targets and all candidate edges and scaled differences remain in the JSON/CSV.

Unmatched registered obsids: `279613034` and `271014105` had **zero** eligible controls; `458908024` had **one** eligible control but failed because that control was assigned to another target. They are not deemed unusual stars or technosignature candidates.

## Population and astrophysical selection cautions

Published sample descriptive medians (250 real spectra): **Gaia G=12.7374 mag**, independently spectroscopically inferred **Teff=5866.5 K**, **logg=4.2295**, **[Fe/H]=−0.081 dex**, published parallax SNR median **93.85** among available records, and Ca II 8542 index median 0.6545. The 172 provisional candidates have median **G=12.8596 mag**. The **original 10,000-star Gaia DR3 registry's median G≈19.58** is *far fainter*; this pilot cannot be extrapolated to that population or to non-FGK stars without new stratified data.

The quality-screened 172 are **NOT independently verified ordinary, quiet or even fully certified LAMOST–Gaia counterparts**. Specifically:
- ESA and Huang+ Gaia ID concordance may derive from related catalog matching pipelines; PM-to-input positional comparison is linear and lacks full covariance, parallax/perspective motion, and instrument-position uncertainty.
- Gaia `phot_variable_flag=NOT_AVAILABLE` does not prove stability. RUWE/non-single-star cuts do not exclude all binaries; high LAMOST SNR and small formal errors do not establish absence of astrophysical activity.
- Ca II index **availability** is enforced; no published calibrated activity quietness threshold or physically classified negative/positive control group has been established.
- **No validated AllWISE / 2MASS survey coverage, extinction, full independent stellar activity classification or full-covariance crossmatch** exists for these 172 under Experiment 008; the results file marks the evidence missing for every spectrum. **Final independently science-certified ordinary control population = 0**, pending further prospective observational tests.
- No infrared excess, spectrum residual significance, candidate anomaly ranking, extraterrestrial origin probability or p-value was computed.

The registered goal was matched cohort *feasibility*, and it has passed within the bright, high-optical-SNR FGK population.

## Reproducibility, files and audit

- [Passing GitHub Actions run 38158825356](https://github.com/gittenssexton/echolens-api/actions/runs/38158825356): **84 tests passed**, original offline 10,000-star Gaia source rebuilt, all exact input source SHA-256s verified, two Experiment 008 runs yielded byte-for-byte identical derived `results.json`.
- **[Full real-data result archive (JSON), durable Echo Lens Drive](https://drive.google.com/file/d/1WpfDXu0CLqWzjxFOTbb5oCblkSAyaodT/view?usp=drivesdk)** — verified 40,752-byte ZIP, 250 per-star records and full matching edges.
- **[Analysis review pack (JSON, 250-row CSV, 40-row matching CSV, chart, README)](https://drive.google.com/file/d/1aXfHBErxAIm3GovQ_e82GksA_gVZfGR3/view?usp=drivesdk)** — verified 118,819-byte ZIP.
- **[Screen attrition plot](https://drive.google.com/file/d/1F4dXT0l4affDOQCthljwcXuBgET9_3cq/view?usp=drivesdk)**.
- CI transient artifact expires 2026-11-10; the final and invalidated outputs remain permanently stored in Echo Lens Drive. Original survey observations and immutable exact source manifests remain in the previously archived Experiment 003, 003G, 006B and 007 folders.

## Next preregistered research priority

**Experiment 009 recommendation (not executed here):** On the frozen 172-strong provisional set, retrieve **real survey-coverage and astrophysical activity** evidence before using these as a scientific null baseline: 2MASS/AllWISE real detections or upper limits with catalog-association ambiguity, bands/instrument flags and extinction; spectral calcium activity and emission-class calibration; multiplicity/crowding and astrometric uncertainty; and a new independent survey validation sample. Freeze the joint sky/brightness/temperature selection rules before infrared-excess scoring. Keep missing values and non-detections separate from true flux and crossmatches. Existing Gaia pilot 10,000 sources and existing LAMOST pilot 250 have **zero overlap**, so do not claim those original 10,000 have independent LAMOST spectra.

Original main branch and Render service untouched. This report documents research design and measured catalog quality, *not evidence of life beyond Earth*.
