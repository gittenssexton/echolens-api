# Stellar registry v0.1

## Existing project audit
Inspected full Git history, all tracked files and every ZIP member before development.
Base: afa2e52bdbeb51efa51885b5640975cb65c3cf94. July 2025 commits uploaded
EchoLensPublicAPI.zip and dependency list. October 2026 PR #1 added app/main.py
and app/__init__.py, restoring the Render uvicorn app.main:app entrypoint.
Root README contained only the repository name. No database, importer, tests,
validated real stellar records or scientific protocol existed in tracked source.

The ZIP contains an unused live Gaia/WISE/MAST prototype and a simple HTML form.
It interpolates a search string into ADQL; chooses the first WISE positional hit;
drops errors/provenance; inverts parallax without a distance model; equates a
MAST time-series entry with variability; and computes an uncalibrated suspicion
index. Preserve the ZIP as historical evidence. Its scores are not ported.
Live /health returned HTTP 200 before work. No Render configuration is changed.

## Schema and provenance
SQLite is the portable pilot registry. `stars` indexes exact string Gaia IDs,
ICRS RA/Dec, G magnitude, BP-RP, parallax and RUWE, retaining every gaia_source
column in typed JSON. `imports` holds the exact query, release, retrieval UTC,
request/response URLs, SHA-256 of original catalog response and field metadata, importer version, field units,
UCDs, datatypes/descriptions and validation report. Integer IDs never pass through
floating point. Null stays null. Published errors/correlations remain unchanged.
The initial snapshot is native FITS served by NASA/IPAC IRSA, with a paired
VOTable for source-column metadata. Preserve the source unit strings, including
nonstandard FITS units, without conversion. FITS NaNs represent missing floating
measurements; blank catalog strings are normalized to null; formatted XML display precision is recorded separately. The IRSA
FITS response includes nine empty trailing transport records; the parser excludes
only trailing records with zero numeric bytes, blank text and false flags, records
the count and rejects any extra nonempty astronomical record. Original bytes are
retained. Gaia source_id and solution_id identifiers are serialized as exact strings.
The snapshot is immutable and compressed; database is rebuilt offline. Publication
of refreshed snapshots requires a new reviewed commit. No request contacts Gaia.

`observations` supports external survey/release IDs, epochs, payloads and provenance;
`crossmatches` supports separation, method, epoch, alternatives and provenance;
`interpretations` separates versioned derived/AI results with input references.
These tables are empty extension points, not a claimed WISE/spectral integration.
No write API is exposed. Catalog GSP-Phot estimates/class probabilities/RV template parameters are returned
under catalog_inferences; other catalog values and flags under measurements.
The field metadata describes native units. Gaia solutions remain calibrated catalog
estimates; “measurement” does not mean unprocessed detector counts.

## WISE and spectroscopic integration contract
Preserve AllWISE external identifier/release and each band's flux/magnitude,
uncertainty, SNR, upper-limit status, cc_flags, ph_qual, ext_flg, blending flags,
observation epoch/baseline and original artifact checksum. Propagate Gaia positions
and covariance to the WISE epoch with proper motion; record all candidate matches,
separation and matching algorithm/version. Inspect ambiguous matches and image
artifacts; never assume a nearest 5-arcsecond hit is the counterpart. Published
Gaia–AllWISE best-neighbour tables may assist but require release/quality review.

For spectra preserve survey/release, visit ID, epoch/time scale, wavelength units
and frame (air/vacuum), flux units, inverse variance/covariance, masks, resolution,
radial-velocity corrections, calibration and checksum/location of original spectrum.
Do not confuse Gaia XP/RVS availability flags with fetched spectra. Cross-survey
source IDs are mappings with evidence, not replacements for the Gaia identity.
Upper limits and uncertain classifications must remain explicit. Payload schema
validation and migration are required before implementing external-survey writes.

AllWISE format: https://irsa.ipac.caltech.edu/data/WISE/docs/release/AllWISE/expsup/sec2_1a.html
