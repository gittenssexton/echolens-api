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

Validation streams gzip through EOF, requiring CRC/trailer success; hashes native
compressed bytes (SHA-256 and MD5); checks FITS primary signature, block alignment
and every HDU payload; requires one table with exactly 10,809,336 rows and scalar
32-bit `obsid`; rejects nonpositive or duplicate observation IDs. It uses temporary
disk plus a separate disposable SQLite key index, without modifying the serving
registry. No catalog uncertainties, fluxes or source IDs are rounded or changed.
Repeated observations of a star remain separate; only observation IDs must be unique.

Tests exercise complete input, absent gzip footer, CRC corruption, truncated FITS,
wrong release row count, invalid IDs and duplicate IDs using small synthetic files.
CI never runs live acquisition. The original source file is required for full
offline revalidation; test fixtures do not establish real-catalog completeness.

Checksums computed here identify the retrieved bytes and can verify storage
transfer. They are not an independently published upstream checksum. Full catalog
recovery does not resolve Gaia counterpart identity, astrophysical normality,
release equivalence of other mirrors, or any anomaly claim.

Keep raw binaries out of Git and archive the validated acquisition, checksums,
schema and original HTTP provenance in Drive. The failed original stays intact.
No API, main branch or Render configuration is changed.
