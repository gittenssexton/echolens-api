# EchoLens Experiment 006 — independent ESASky copy of LAMOST DR9 observation metadata

**Protocol committed 2026-10-11 before any ESASky table-data query.** This is **provenance and source-identity feasibility**, not an extraterrestrial-life test, clean-control certification, nor a blinded experiment. The reported 5.1201" catalog-coordinate discrepancy and original LAMOST DR9 bright-source fiber-offset hypothesis were already known.

## Research question
Can the **ESA ESASky LAMOST DR9 LRS General Catalog** independently provide trustworthy, obsid-linked `obsDate` for the 250 frozen original LAMOST/Huang+ 2024 DR9 spectra, even though official LAMOST DR9's bulk CSV/FITS downloads require authorization? Is the ESA copy sufficiently documented to recover `ra_obs, dec_obs, offsets, offsets_v`? If not, use the dates only as third-party context and leave fiber-offset and crossmatch certification unverified.

**Key provenance warning:** ESA's publicly described LAMOST DR9 General Catalog cites 11,211,028 spectra, while the official LAMOST DR9 **v2.0** General Catalog describes 10,809,336 spectra. These may not be identical curation or release versions. NEVER silently substitute one catalog for the other; compare release IDs and exact obsid entries before use. An ESASky observation date is published LAMOST-derived metadata *re-exposed by ESA*, not independent spectroscopy.

Original references:
- ESA ESASky catalog description: https://www.cosmos.esa.int/web/esdc/esasky-catalogues (LAMOST DR9 General)
- Public ESA TAP service: https://sky.esa.int/esasky-tap/tap
- LAMOST DR9 v2 official documentation: https://www.lamost.org/dr9/v2.0/doc/lr-data-production-description
- Original 250 obsids and native VizieR bytes in Experiment 003 archived GitHub Actions run `38146071576` and durable Echo Lens Drive.
- Gaia ID audit in run `38146667656`.

## Pre-data metadata gate
1. Query the documented ESA TAP `TAP_SCHEMA.tables` and `TAP_SCHEMA.columns` for tables with names or descriptions containing `lamost`; **do not assume the table identifier**.
2. Save exact raw bytes, endpoint/request, HTTP response details, retrieval UTC, query status, SHA-256, parsed metadata and all candidate table schemas.
3. Only if one unambiguous ESA LAMOST DR9 **LRS General** table is identified, with a documented **exact obsid** column and dated `obsdate` column, may an observation lookup be initiated in a separately reviewed acquisition step. Do not accept an MRS table or wrong DR9 version. If multiple candidates exist, stop and list them for human scientific review; do not choose one on convenience.
4. Prefer bounded, 25-obsid chunks with `SELECT` only the actually documented field names, `MAXREC` above batch size, strict TAP `QUERY_STATUS=OK` and no `OVERFLOW`. Publish zero-count/no-match outcomes; no substituting IDs.

## Frozen source identities
All 250 exact decimal `obsid` values originate from Experiment 003, preserved unchanged. The first diagnostic obsid is `655310123`, published Gaia DR3 ID `876451818359869824`. Separate target and selection-bias conclusions remain forbidden. Any recovered date is held as `esa_lamost_dr9_obsdate` with its precise source and archive version, not renamed `official_lamost_dr9_v2_obsdate`.

## Acceptance
A successful schema discovery is *metadata feasibility only*. A successful date retrieval requires unmodified response bytes and checksums, exact IDs, declared date format, distinct obsids, no duplicates, and a verified documented release identity. Fiber-offset confirmation requires actual official LAMOST DR9 v2.0 `offsets/offsets_v` or original FITS header (not merely ESASky date). Complete Gaia source-association certification also requires observation-epoch propagation and full uncertainty model.

Do not modify `main`, Render API, the 10,000-star Gaia measurements, previous controls, or past failed results.
