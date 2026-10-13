# LAMOST DR9 v2.0 LRS source recovery

Engineering run DR9-LRS-SOURCE-REPAIR-20261013. This recovers one original
catalog; it is not a new stellar or technosignature experiment.

## Existing evidence

The preserved Drive file `1VxCToFf29cfL9tfQIWcfw_kgkVZ6025X` is 17,984,508
compressed bytes. Its recorded integrity audit finds no complete gzip footer,
159,586 readable rows versus 10,809,336 declared rows, and `whole_file_valid=false`.
It remains preserved in Source Archives; never append new bytes to it or ingest
its readable prefix as the whole release. The two newer MRS input/stellar copies
also failed independent gzip checks. They are outside this single-file repair.

The official catalog HTML contains an image link that text-only page extraction
did not expose: `catdl?name=dr9_v2.0_LRS_catalogue.fits.gz`. A bounded request on
2026-10-13 returned HTTP 200 and gzip magic. A Range request was not honored:
no Content-Range, ETag, Content-Length or Last-Modified was supplied. This is
access evidence only, not evidence of a complete catalog. Do not claim resumption
when a server sends HTTP 200 instead of a validated byte-range response.

Source page: https://www.lamost.org/dr9/v2.0/catalogue

## Recovery and acceptance

```
python -m scripts.repair_lamost_dr9 /path/to/new-acquisition-directory
python -m scripts.repair_lamost_dr9 --validate-file /path/to/catalog.fits.gz
python -m unittest tests.test_lamost_repair -v
```

The downloader refuses existing destination files. It saves UTC, exact source
and final response URLs, HTTP status and available headers, writes `.part`, and
only renames the new file after validation. Errors leave partial bytes and failed
provenance intact. A timeout is a failed acquisition, never an empty catalog.
The transfer is capped at 4 GiB compressed, 4 GiB uncompressed, and 30 minutes;
socket reads time out after 90 seconds without data. An extension of these caps
must be recorded explicitly, not silently applied to the same run.

The initial local transfer was deliberately interrupted after preserving partial
checkpoints. A new cloud attempt records `--max-seconds 5400` (90 minutes);
the 4 GiB size caps and every scientific integrity gate remain unchanged.
The separate acquisition workflow runs only by explicit dispatch or the
`[acquire-lrs-catalog]` push marker on this research branch. Ordinary code pushes
skip its network job. It saves acquisition bytes in 64 MiB parts plus an assembly manifest with explicit
validation status. Failed bytes remain unvalidated and must never be ingested.
GitHub artifacts expire after 30 days and require durable Drive archival.

Validation streams gzip through EOF, requiring CRC/trailer success; hashes native
compressed bytes (SHA-256 and MD5); checks FITS primary signature, block alignment
and every HDU payload; requires one table with exactly 10,809,336 rows and scalar
32-bit `obsid`; rejects nonpositive or duplicate observation IDs. It uses temporary
disk plus a separate disposable SQLite key index, without modifying the serving
registry. No catalog uncertainties, fluxes or source IDs are rounded or changed.
Repeated observations of a star remain separate; only observation IDs must be unique.

Tests exercise complete input, absent gzip footer, CRC corruption, truncated FITS,
wrong release row count, invalid IDs and duplicate IDs using small synthetic files.
The ordinary registry test workflow never runs live acquisition. The original source file is required for full
offline revalidation; test fixtures do not establish real-catalog completeness.

Checksums computed here identify the retrieved bytes and can verify storage
transfer. They are not an independently published upstream checksum. Full catalog
recovery does not resolve Gaia counterpart identity, astrophysical normality,
release equivalence of other mirrors, or any anomaly claim.

Keep raw binaries out of Git and archive the validated acquisition, checksums,
schema and original HTTP provenance in Drive. The failed original stays intact.
Main and Render configuration are unchanged. The later staging work adds
optional read-only observation routes on this unmerged research branch.

## Cloud attempt 002 outcome

Run https://github.com/gittenssexton/echolens-api/actions/runs/38328672226
at commit `237b435d3771bdab51cd779562083f00dea9cd80` received 95,638,481 bytes
and ended after approximately five minutes, before its 90-minute budget. HTTP
reported 200 without length or identity headers, but gzip raised `EOFError`
before the end-of-stream marker. This is an incomplete transfer, not a successful
catalog acquisition. The validator did not rename or promote the partial file.
All five offline integrity tests passed on the runner.

Partial SHA-256 recorded by the runner:
`4492840d52ede2dfc0f24e1de405949a9d2695949eee68e23882efb5915bdde4`.
The original failed cloud workflow uploaded only metadata, so the cloud partial
bytes are not recoverable from its artifacts. The workflow now preserves both
failed and validated acquisition bytes with explicit status; this change is
not evidence that the failed cloud bytes were retrospectively recovered.

Durable failure metadata:
https://drive.google.com/file/d/1D9DquiIzQq1pnsXFUIVnNbMS6nUwfUQW/view

The independent local partial contains 330,301,440 bytes and remains preserved
in five fragments under `LOCAL_ATTEMPT_001_PARTIAL_DO_NOT_INGEST`. It is not the
cloud partial and must not be combined with it.

The linked official FTP route redirects to LAMOST/NADC authentication. The public
package directory lists spectra archives, not this general catalog. A complete
provider file or an authenticated resumable source is needed before catalog
import. No repeated unattended retry has been scheduled, no observation rows
from the incomplete transfer were imported, and main/Render remain unchanged.

## Auxiliary source integrity run 2026-10-13

Run `DR9-LRS-AUXILIARY-INTEGRITY-20261013` validates two smaller, existing
archive files, not recovery of the general catalog. Both native gzip files pass
CRC/trailer through EOF, FITS HDU/block/payload checks, independently published
release row counts, and positive unique `obsid` checks. Fresh bounded downloads
from the official `catdl` links are byte-identical to the archived files.

| Product | Observation rows | Native gzip bytes | FITS columns |
| --- | ---: | ---: | ---: |
| White dwarf catalog | 14,691 | 1,951,285 | 39 |
| QSO emission-line feature catalog | 18,142 | 8,712,340 | 180 |

Expected counts come from https://www.lamost.org/dr9/v2.0/ (WD Star Catalog
and Qso Emission line Feature Catalog), independently of the FITS headers.
The general QSO spectrum count of 74,997 is a different product and is not the
expected row count of this line-feature subset.

Full schema, native checksums, UTC retrieval times, HTTP provenance and archive
Drive IDs are in `reports/lamost_dr9_auxiliary_validation_20261013.json`.
Auxiliary archival evidence folder:
https://drive.google.com/drive/folders/1A6TEfOmuJzXouXEsLxzKsst5xpuPC_DS

Offline reproduction from the original files:

```
python -m scripts.audit_lamost_auxiliary wd /path/to/dr9_v2.0_LRS_wd.fits.gz
python -m scripts.audit_lamost_auxiliary qso /path/to/dr9_v2.0_LRS_qso.fits.gz
```

Replay requires the exact frozen compressed SHA-256 before structural checks;
changed input bytes require a new audit. Both real files passed offline replay,
and one-byte-truncated copies were rejected by the identity gate. Original
uncertainty columns and units are recorded from FITS headers without changing
or imputing values. White-dwarf `teff`/`logg` and their uncertainties are survey
pipeline estimates, not EchoLens AI interpretations.

Observation rows are not necessarily unique physical sources. Neither product
certifies Gaia counterpart identity or astrophysical normality. White dwarfs
are a specialized population, and QSOs are not ordinary stellar controls.
These audits establish complete source files for later explicit protocols;
no selected experiment, crossmatch or anomaly test has been run on them,
and the incomplete main catalog remains blocked. No serving data was imported.
