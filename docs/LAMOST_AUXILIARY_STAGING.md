# LAMOST DR9 auxiliary observation staging

Run `DR9-AUXILIARY-STAGING-20261013` extends the verified-source work in PR33.
It is an isolated offline SQLite store, not a deployment or a scientific experiment.
The general LRS catalog remains incomplete and blocked.

## Inputs and native preservation

The exact WD and QSO line-feature gzip files are frozen by compressed SHA-256
in `scripts/audit_lamost_auxiliary.py`. Staging requires complete gzip/FITS
validation, independently published row totals and positive unique observation
IDs before any database is published. The two products contain 14,691 and
18,142 observation rows (32,833 total), respectively. This is not a count of
unique physical stars; QSOs are not stars or ordinary stellar controls.

Every row stores its exact native FITS bytes, SHA-256, row index and FITS byte
offset, plus decoded survey values and native schema (field names, formats,
units, null encodings). Imported headers and input provenance remain attached
to each product. Implementation hashes identify the decoder, source-audit and
integrity-validator versions. Survey fitted parameters and uncertainties remain
survey estimates, separate from any EchoLens AI interpretation.

Native float32/float64 precision is retained. Nonfinite JSON values are null
with explicit native-encoding flags, while raw row bytes retain the original
NaN payloads. Integer null encodings and undocumented survey sentinel values
remain literal, with FITS-null flags where declared. Nothing is imputed or
rounded. Character padding is removed from decoded display strings only;
exact space/NUL padding remains in the raw row. Real-source testing found
NUL-padded Gaia IDs, covered by a regression test.

The source observation key is `(product, obsid)`, so an observation appearing in
both specialized products is not collapsed. Indexed `reported_gaia_source_id`
is only a syntactically valid identifier reported by LAMOST; it is not a physical
crossmatch, foreign key to the Gaia registry, or counterpart certification.
These sources do not replace the missing general catalog.

## Reproduction and queries

```
python -m scripts.stage_lamost_auxiliary build \
  --wd /path/to/dr9_v2.0_LRS_wd.fits.gz \
  --qso /path/to/dr9_v2.0_LRS_qso.fits.gz \
  --output /path/to/new-staging.sqlite3
python -m scripts.stage_lamost_auxiliary search \
  --db /path/to/new-staging.sqlite3 --product wd --obsid 101076
python -m scripts.stage_lamost_auxiliary inspect \
  --db /path/to/new-staging.sqlite3 --product wd --obsid 101076
python -m unittest tests.test_lamost_repair tests.test_lamost_staging -v
```

Search supports product, observation ID and exact reported Gaia ID, with a
maximum of 200 returned rows. Inspect returns the survey values, uncertainties,
field schema, provenance and native row reference. Queries open SQLite read-only.
Missing files are not created. Existing databases are never overwritten;
failed inputs never publish a candidate. Unsupported FITS types or scaled
fields fail explicitly instead of receiving an approximate decoder.

## Real-data validation and archive

`reports/lamost_staging_validation_20261013.json` records row counts, SQLite
integrity, source hashes, all-row native-byte comparisons, search/inspection
checks and the exact database/archive hashes. All 32,833 native rows were
compared byte-for-byte against their source FITS payloads. The compressed
SQLite artifact was fully decompressed through gzip EOF and checked against
the original database SHA-256.

Durable data and validation records:
https://drive.google.com/drive/folders/12eTyBoUFKBXrWXjl8S9XXKjRGVtYXnEv

Use the artifact manifest to verify the archive hash, decompress the SQLite
file, and verify the database hash before querying. Rebuilding preserves the
logical data/native rows; UTC staging provenance makes a new database's binary
hash different. Binaries remain outside Git. No Gaia serving database, main branch or Render configuration is changed.
An optional read-only observation API is now implemented on the research branch: Future survey adapters
can use this native observation/schema/provenance pattern under explicit
crossmatch and population protocols.

## Optional API on the research branch

Set `ECHOLENS_OBSERVATIONS_DB_PATH` to the separately verified SQLite snapshot
to enable `GET /observations`, `GET /observations/catalogs` and
`GET /observations/{product}/{obsid}`. Search accepts product (`wd`/`qso`),
obsid, exact `reported_gaia_source_id`, limit (1–200) and offset (0–100000).
It does not join unverified identifiers to the serving Gaia stellar registry.

Without a configured/available staging database the new routes return 503;
health and existing Gaia routes retain their behavior. All queries open the
snapshot read-only; unavailable files are never created, invalid queries return
422, missing observations return 404, and detected native-row tampering is not
served. Details include survey values, uncertainty fields, schema units, source
provenance and exact native-row references.

The API is tested on the branch and has not been deployed to Render. Configure
verified data and review PR33 before any separate deployment decision.
