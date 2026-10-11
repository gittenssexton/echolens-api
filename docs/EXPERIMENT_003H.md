# EchoLens Experiment 003H — observation-epoch crossmatch review (engineering protocol)

**Date frozen:** 2026-10-11. This is a *post-hoc follow-up* to the known Experiment 003G 5.12-arcsecond position discrepancy, **not a blinded preregistration or technosignature test**. The exact 250 LAMOST DR9 source IDs and Gaia DR3 observations remain unchanged.

## Why the next task is not anomaly scoring
Official LAMOST DR9 v2 low-resolution General and AFGK Parameter catalogs have `obsid`, `obsdate`, `mjd`, `ra_obs`, `dec_obs`, `offsets`, `offsets_v`, `gaia_source_id`. The pre-existing VizieR Huang+ 2024 activity catalog does **not** include actual observation dates. Its `RAJ2000` / `DEJ2000` are catalog coordinates in a J2000 frame, **not verified pointing coordinates at observation epoch**. The Gaia DR3 positions refer to reference epoch 2016.0. Therefore naive differences must not certify or reject matches.

Sources:
- https://www.lamost.org/dr9/v2.0/doc/lr-data-production-description
- https://www.lamost.org/dr9/v2.0/doc/faq
- https://vizier.cds.unistra.fr/viz-bin/VizieR-3?-source=J%2FApJS%2F272%2F6
- Frozen input artifacts: LAMOST experiment 003 Actions run `38146071576`, Gaia audit run `38146667656`; Drive archival hashes/provenance as in PR #9.

## Phase A — reproducible *epoch-bound diagnostic*, no new catalog claims
Use the *unaltered* 250-record LAMOST Experiment 003 result and 250-record Gaia DR3 audit. Validate 1:1 `obsid` -> exact `GaiaDR3`, input schema and number of objects. Compute:
- angular separation between existing uncorrected Gaia (2016) and LAMOST `RAJ2000/DEJ2000`, preserving both original positions.
- Gaia total proper motion norm `hypot(pmra,pmdec)` mas/yr; expected displacement upper bound across **2011-10-24 through 2021-06-30** using distance in Julian years from Gaia epoch 2016.0. This bounds *linear proper motion alone* (not annual parallax, precession, uncertainty in LAMOST coordinates, fiber offsets, or blends).
- Conservative triangle-inequality residual lower bound `max(0, uncorrected separation - bound)`; independently flag cases that cannot get under a 3-arcsecond **review radius** by linear proper motion during the stated LAMOST release observation window. This is triage only, **not proof of misidentification** and not a scientific exclusion.
- For missing Gaia PM or errors, report `not_assessable`. Preserve unknown observation dates: never synthesize observation MJDs or approve a match from this bound.

Publish all 250 records, raw-input SHA-256, sources and reproducible JSON; separately report a priority list of manual-review cases. No observations are changed. Outputs remain derived diagnostics in `reports/experiment_003h`.

## Phase B — official *actual observation metadata*, when accessible
Retrieve exact `obsid` rows from LAMOST DR9 **v2.0** LRS General Catalog. Preserve original catalog version/download URL, original unmodified bytes/format, file SHA-256, retrieval UTC, all units. Ingest only exact selected 250 obsids; verify uniqueness, every required field, no negative fiber offsets and valid dates. Track missing rows and conflicts without substitution. Do **not** use VizieR `recno` as a stellar identity.

A strict `--official-csv` ingestion adapter must allow replay from a *user-authorized export* of the official catalog, with exact 250 IDs and all `obsdate, mjd, ra_obs, dec_obs, offsets, offsets_v` fields. If the public site blocks an unauthenticated programmatic catalog request, leave Phase B unexecuted — don't guess private endpoints, fabricate MJDs, claim epochs are resolved, or use value-added third-party epochs without an explicit separate provenance/source version.

## Phase C — true astrometric comparison (only after Phase B)
Propagate Gaia ICRS position, PM and full covariance from 2016.0 to the recorded LAMOST observation epoch; include Gaia parallax where geometrically relevant and record missing RV/perspective effects. Compare to the **published fiber pointing `ra_obs,dec_obs`** and any deliberate `offsets_v`, not automatically `RAJ2000`. Check neighboring Gaia candidates, crowding, measurement quality, ambiguities and original LAMOST spectral flags. Predeclare posterior/matching decision criteria separately before classifying clean links.

The first result cannot be described as a validated control group. No current discovery ranks, IR excesses, or AI-origin probabilities will be produced.
