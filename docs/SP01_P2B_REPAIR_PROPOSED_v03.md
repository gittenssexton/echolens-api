# SP01 sampling and calibration repair — proposed v0.3
Prepared 2026-10-18 UTC (October 17, New York).
Status: PROPOSAL FOR REVIEW. No existing protocol, cohort role, scientific status, repository or deployment changed. No spectra or holdout outcomes opened.

## Decision
Keep the old 20-source work as preserved evidence. Propose using it for software development only, subject to reviewer disposition. Do not recycle exposed stars into the new calibration or holdout sets. Preserve the existing unopened holdout assignment as historical; do not automatically adopt it for the new design.

Repair sample construction before adding spectra. Separate baseline construction, threshold calibration and held-out evaluation. A successful engineering test remains distinct from a calibrated scientific claim.

## What is implemented
scripts/sp01_p2b_repair.py is an offline metadata-selection prototype. It:
- Rejects a declared truncated/bounded or incompletely paginated source frame.
- Checks input byte hash and expected row count.
- Requires exact source IDs, one row per source and explicit ordinary eligibility; positive controls cannot enter the ordinary frame.
- Requires reviewed group metadata from all known visits, with source-system/reduction-group relationships represented as keys.
- Builds transitive connected components of shared keys.
- Excludes components connected to previously exposed sources, including exposed stars outside the eligible frame via their exposure-group ledger.
- Selects at most one representative per component, by a fixed source-ID hash.
- Uses four existing Teff/SNR strata; independently hash-orders representatives within each.
- Assigns template, calibration and holdout roles by an interleaved fixed rule.
- Stops on shortages without relaxing criteria.
- Creates only a proposed metadata manifest and refuses to overwrite an existing output.

Nine synthetic tests passed. They cover order invariance, quotas, component separation, transitive exposure, exposed objects outside the candidate frame, missing metadata, truncated pools, hash/count mismatch, malformed IDs, duplicate IDs, natural-positive contamination and shortage behavior.

These are software checks, not proof that a real source frame is complete or that supplied group keys capture every dependence. No real replacement cohort has been selected.

## Why this changes the previous design
The pinned acquisition code uses SELECT TOP 180 ... ORDER BY GaiaDR3 before hashing. Hashing that bounded pool cannot recover the missing sky coverage. The October 17 review correctly flags concentration, although recounting the pinned manifest yields 13/20 sources in its two largest observation-ID prefixes, not 14/20. Prefix counts alone do not establish physical batch boundaries.

The existing transport amendment already discloses the detrended VizieR source substitution for feasibility. A new approved scientific sampling amendment is still needed.

## 1. Source-frame contract
Preferred authority remains original GALAH DR4 allstar for one-source selection plus allspec for observation mapping. A different source can be proposed only with explicit reviewer-approved scope and field comparison; never silently declare the derived table equivalent.

Retrieve metadata only, not spectra:
1. Freeze the exact release, scientific eligibility expression, required columns and deterministic pagination strategy.
2. Obtain the entire declared eligible frame. Page-size limits are transport mechanisms; fetch all pages, preserve every query/response hash, and check completion/overflow indicators.
3. Independently reconcile expected counts, page boundaries, unique IDs and representative-visit rules. No TOP-N remainder may be discarded.
4. Preserve original eligibility cuts from v0.2 unless an amendment explicitly changes them.
5. Record actual coordinates, sky distribution, Teff/SNR distributions, visits and available batch/system/cluster metadata before selection.
6. Compare frame and proposed sample coverage without outcomes. Unexpected skew triggers review, not repeated seeds until a preferred answer appears.

Full-frame means the declared eligible population, not the entire Galaxy or an unbiased stellar census. Eligibility itself conditions the study.

This package does not implement provider acquisition, native field normalization, eligibility certification or complete frame verification. A metadata boolean cannot prove those facts.

## 2. Independence and exposure contract
Use provider-documented field/exposure/reduction identifiers and known physical-system relations. Do not infer complete field or night identity solely from an sobject_id prefix.

Group keys must cover all known visits of every candidate. Connected components propagate shared-system and shared-reduction relationships across sources. The prototype takes one star per component across all three new roles. This is conservative and may cause shortages; it is a proposed engineering rule, not proof that all remaining observations are independent.

Exposure ledger:
- Include the 20 already inspected P2B sources.
- Include the three prior P0/P1/P2A sources already named in v0.2.
- Reconcile any additional exposures from the workstream logs.
- Map exposed sources to verified groups even when they fail current eligibility.
- Unknown group mapping prevents a new manifest.
- Related-system exposures must propagate with the reviewed system mapping.

Known positives are a separate cited source list. They do not contribute to the ordinary-null denominator or template construction. Selecting and acquiring the ten positives remains a separate reviewed step; this sampler does not claim to implement that step.

## 3. Proposed sample sizes and roles
Default proposal: 60 new ordinary sources plus 10 separately reviewed natural positives.
- Template fitting: 20 (5 per existing Teff/SNR stratum).
- Calibration: 20 (5 per stratum).
- Holdout: 20 (5 per stratum).
- Natural positives: 10, excluded from the ordinary sample.

This increases the former 40 ordinary-source design to 60 to separate nuisance-model fitting from threshold calibration. It is a reviewable design choice, not authorization for acquisition. The current 20 exposed stars can support coding and exploratory diagnostics but should not supply a supposedly representative frozen template.

At most one source per known connected group changes inclusion probabilities. The representative rule is fixed before selection. A shortage after that rule does not prove no combinatorial allocation exists; it means this registered rule cannot fill quotas. Any alternative needs a new version, not an adaptive hidden fallback.

## 4. Proposed score and baseline
Use the Claude R1–R5 proposals as review inputs, with explicit safeguards:
- Primary endpoint: absorption-only, signed line contrast, if confirmed as the intended Experiment 002-A question. Positive residuals remain separate diagnostics.
- Fit a wavelength-dependent baseline from TEMPLATE sources only, with an agreed rest-frame convention and stratum model.
- Freeze template, masks, line exclusions, smoothing/registration choices and all nuisance-fitting settings before opening calibration residuals.
- Use exactly the same frozen template and transformation for calibration and holdout stars. Do not let calibration stars define their own baseline.
- Any per-star robust normalization must be predeclared and applied identically, with finite/zero-scale failures recorded. Validate signal attenuation with development injections.
- Use a continuum-orthogonal, LSF-matched filter. Native camera/LSF quality must define the eligible analysis arms.
- Assumed LSF can be used in labeled sensitivity experiments; it does not fill missing instrumental validation.
- Define one source-level extremum across a fixed wavelength family. Repeated pixels or visits do not become independent null samples.
- Missing masks, uncovered lines and failed preprocessing are not negative detections.

This package deliberately does not implement a scientific score from unadjudicated choices. Before score coding, freeze the exact kernel, wavelength frame/grid, exclusion list, normalization and handling of incomplete LSF.

## 5. Calibration limits and evaluation
Twenty calibration stars are inadequate for a rare-event discovery claim. Five per stratum are even coarser.

Under exchangeable, comparably scored independent null units and conservative ties:
- A rank p-value has minimum 1/(N+1).
- A within-stratum calibration of five gives minimum 1/6.
- Pooling twenty would give minimum 1/21 only if pooling/exchangeability is justified; strata and shared instrument effects do not guarantee it.
- The earlier approximate 0.95 expected exceedances among 20 holdouts applies to the stated idealized pooled strict-maximum rule, not automatically to this stratified design.

Therefore this v0.3 proposal is a source-separated feasibility and descriptive calibration pilot. It must not advertise a 1% false-alarm threshold or five-sigma significance. Keep every source-level score and denominator. Use injections and natural positives to characterize conditional sensitivity, not to manufacture real-null tail support.

If the goal is a confirmatory rare-event test, first specify the target error rate and family, then plan a larger independent calibration/validation design or a defensibly validated null model. Do not choose a star count solely because it reaches one p-value grid point.

Sequencing:
1. Develop algorithm using exposed data/synthetic injections.
2. Review full metadata frame and proposed group-disjoint roles.
3. Approve and acquire template data only.
4. Build/freeze template and score implementation.
5. Approve and open calibration data; fit only the registered threshold.
6. Freeze threshold, exclusions, failure rules and evaluation plan.
7. Independent reviewer permits holdout access.
8. Open once, report outcomes and missingness; any retuning creates a new study.

## 6. Remaining prerequisites
- Verified full metadata frame and acquisition completeness evidence.
- Provider-grounded reduction-group/all-visit and exposure mappings.
- Approval of original-versus-derived catalogue authority.
- Reviewer acceptance of the new three-way split and sample sizes.
- Exact score specification and instrument QA.
- Explicit error-rate/sensitivity goal for any later confirmatory expansion.

None is silently assigned or approved here. The existing samples and histories remain intact.

## Running the prototype
Python standard library only.
```
python -m unittest discover -s tests -p test_sp01_p2b_repair.py -v
python -m scripts.sp01_p2b_repair --frame frame.json --evidence evidence.json --exposed exposed.json --output proposed_manifest.json
```

frame.json is a list of metadata rows with:
source_id (exact decimal string), stratum, ordinary_eligible=true,
natural_positive=false, group_metadata_complete=true,
group_keys (nonempty list of reviewed system/reduction tokens).

evidence.json requires:
scope="full_declared_eligible_frame", truncated=false, all_pages_complete=true,
grouping_reviewed=true, source_release, query_record, completeness_record,
grouping_record, expected_rows, frame_sha256.
The four record/release fields identify actual preserved evidence; fixture labels belong only in tests.

exposed.json requires:
source_ids (all known exposed exact IDs), group_keys (all mapped exposure groups),
group_mapping_complete=true, record (evidence reference).
An incomplete mapping must not be marked complete simply to run the tool.

## Evidence and provenance
Baseline commit checked unchanged in PR30:
97a26f8a79c6725fd313be9b6218bf04269f5982
https://github.com/gittenssexton/echolens-api/pull/30

Acquisition mechanism:
https://github.com/gittenssexton/echolens-api/blob/97a26f8a79c6725fd313be9b6218bf04269f5982/scripts/sp01_p2b_acquire_vizier.py

Original selector:
https://github.com/gittenssexton/echolens-api/blob/97a26f8a79c6725fd313be9b6218bf04269f5982/scripts/sp01_p2b_select.py

Protocol:
https://github.com/gittenssexton/echolens-api/blob/97a26f8a79c6725fd313be9b6218bf04269f5982/docs/SP01_P2B_PROTOCOL.md

Existing feasibility amendment:
https://github.com/gittenssexton/echolens-api/blob/97a26f8a79c6725fd313be9b6218bf04269f5982/docs/SP01_P2B_TRANSPORT_AMENDMENT.md

October 16 review:
https://drive.google.com/file/d/1NTQDysdy4X0zSpSxuHDSXcC-XWOhrLRA/view
October 17 addendum:
https://drive.google.com/file/d/1lew8DDaAt2ihN3bkCn_DSy94njqkuGMb/view

The new sampler and this proposal are local review artifacts, not changes to these source documents.


## Repository review tracking — 2026-10-21
This proposal is staged on its own branch from main. It references governance issue #31 and the existing scientific work in PR #30; it does not supersede or amend that PR or its frozen history.

No provider acquisition or spectral execution workflow is added. The existing offline test workflow discovers the synthetic tests. Review and real metadata acquisition remain next steps before any proposed real-sample selection.
