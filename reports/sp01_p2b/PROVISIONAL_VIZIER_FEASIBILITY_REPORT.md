# EchoLens SP01-P2B — Real-star VizieR feasibility cohort (2026-10-12)

**Outcome: 50 real Gaia DR3 source IDs assembled in a PROVISIONAL cohort. Confirmatory science gate remains closed.**

## Verified executed acquisition
- Data Central official GALAH DR4 `main_star` was not accessible through tested public endpoints: legacy TAP returned HTTP 400 with unknown table; REST returned HTTP 403. These transport failures are archived, not hidden.
- Replaced ONLY the *engineering feasibility input* with the **Kos et al. (2025) VizieR detrended GALAH DR4** table `J/A+A/703/A104/catalog` (917,588 rows). The source is a derived catalogue, **not original GALAH DR4 allstar/main_star**. No statement of interchangeability is made.
- Natural positive labels independently sourced from **Escorza et al. (2026)** VizieR `J/A+A/712/A111/catalog`, 1,059 published s-process-rich stars. They are not matched ordinary dwarf controls.
- Retrieved 180 metadata records per each of four prespecified ordinary strata (720) plus 150 preselected independent s-rich candidates (150) = **870 unique source records** available to preregistered selector. Original provider CSV responses, exact queries, timestamps and SHA-256s are archived.
- Applied identical `echolens-sp01-p2b-v1` source-ID-hash and quality selection rules without inspecting any new spectra. Final counts: **20 calibration controls, 20 withheld ordinary controls, 10 independently catalogued s-process-rich natural positives**. The 40 ordinary sources occupy four Teff/SNR3 strata, **10 per stratum** (5+5 calibration/holdout). Exact 64-bit Gaia IDs preserved as decimal strings.
- Source-overlap protection excludes previously used Gaia IDs 3064554891927687296, 6053735173729807872, and 6130627011126533760. All 50 selected IDs are unique; repeated visits do not create independently counted stars.
- Offline replay of the GitHub Actions original-input candidate and label CSV files independently reproduced both `provisional_detrended_manifest.json` and `.csv` **byte for byte**.

## Numerical metadata summaries

| Group | Distinct stars | Median Teff (K) | Median SNR3/pix | Median logg |
|---|---:|---:|---:|---:|
| Ordinary calibration | 20 | 5581 | 59.9 | 4.38 |
| Ordinary holdout | 20 | 5594 | 61.2 | 4.37 |
| Published s-rich positives | 10 | 4663 | 64.3 | 2.44 |

## Complete input-bundle provenance and replay
- VizieR original-response bundle SHA-256: `e55f09df098a3ce2d9ab3071e2436671adfefd73b12fed015855a988572d56c4`.
- Provisional output manifest JSON SHA-256: `703d28460aba7b289b62adcf07e93a76fb5df7723f89543672046cb4ee41162e`.
- Published independent-label response SHA-256: `645e5ad807a12bb1489de8fc0ff09b41708f45b464f6f2ae866f7b51d5c2f508`.
- GitHub Actions source run #9: https://github.com/gittenssexton/echolens-api/actions/runs/38283867273 (success, workflow acquisition + provisional selector). Original response archive `sp01-p2b-tap-attempt-9` is attached to the run and separately retained in EchoLens Drive.
- Source release and table queries recorded verbatim in `provenance.json`; no fabricated stellar rows or errors were used.

## Scientific limitations and next gating experiment
1. **This is not a null-science validation.** It contains no new spectra, mask checks, line identifications or anomaly scores. The 50-star manifest is provisional pending original GALAH `main_star` parameter cross-checks and explicit approval of the source substitution for the scientific protocol.
2. This is a **bounded, ID-ordered TAP candidate pool**, not a GALAH-complete probability sample. Comparing calibration and holdout does not make the population statistically representative or eliminate selection bias.
3. Positive s-process-rich sources are not matched in Teff/gravity/SNR to the ordinary dwarfs. Appropriate only as separately labelled natural positives; not as matched statistical null controls.
4. Same-source GALAH repeat visits must remain linked; ensure target metadata errors and known binaries remain excluded or separately analyzed.
5. Acquire allspec analysis spectra for a **small calibration-only subset** before considering the whole cohort, verify SHA-256, arm coverage, uncertainties, `mob` polarity and fitted-model leakage, and obtain native LSF where accessible. Holdout IDs must remain unopened until model/threshold freeze. Infrared/source-level or line-search false-alarm conclusions are not supported.

## Source citations
- Official original GALAH DR4: https://www.galah-survey.org/dr4/the_catalogues/
- Kos et al. 2025 derived catalogue: https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=J%2FA%2BA%2F703%2FA104
- Escorza et al. 2026 positive catalogue: https://vizier.cds.unistra.fr/viz-bin/VizieR?-source=J%2FA%2BA%2F712%2FA111
- Research protocol `docs/SP01_P2B_PROTOCOL.md` and source-substitution amendment `docs/SP01_P2B_TRANSPORT_AMENDMENT.md` on the **unmerged research branch**.
