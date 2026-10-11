# EchoLens R01-A: cloud acquisition preflight

**Status (2026-10-11 UTC): prepared, not executed.**

## First pilot observation

- Public archive listing: https://breakthroughinitiatives.org/opendatasearch?file_type=all&order=desc&page=15&perPage=100&project=GBT&search=Search&sort=centerfreq
- Telescope: Green Bank Telescope (GBT)
- Target label: NGC6822
- Start time: 2019-12-24 21:09:59 UTC
- File type: HDF5
- Archive-listed size: 3,276,424,687 bytes (~3.28 GB)
- Archive-listed MD5: `-` (unavailable); no verified SHA-256 exists yet.
- Full download URL / observation ID: **pending archive detail verification**.
- Companion cadence: three NGC6822 entries alternate with HIP96950, HIP97423 and HIP97063. These provisional ON/OFF classifications need header/observing-log confirmation before science.

## Cloud workflow (notebook)

`R01_GBT_Cloud_Acquisition.ipynb` is designed for Google Colab. It reads a specific row and attempts to extract its download link. It fails closed if the target row or URL is ambiguous, if redirects point outside known archive hosts, or if the server-reported byte count differs from the archive. Manual URL entry is allowed **only** after reviewing the exact archive record. The notebook defaults to `RUN_DOWNLOAD=False`.

If the URL/size preflight succeeds, the operator can explicitly set `RUN_DOWNLOAD=True`. Only then is the source file downloaded to **temporary Colab storage**; SHA-256 and MD5 are calculated and the raw file is uploaded into the existing R01 Google Drive folder (ID `1b6s5yaaNDpjhDtIaobXv1eQ24U6BvXl7`) with resumable Drive API upload. Drive file byte count and MD5 are checked before success is reported, and a provenance manifest is created in that folder. Colab runs in the cloud, but **the operator must authenticate their Google account once**; do not share or commit Google OAuth tokens.

Because the archive does not provide a published independent digest for this row, comparing calculated MD5 to Drive's MD5 ensures upload integrity, **not independent authenticity of the source bytes**. Any HTTP-only source transport is marked with a warning. If URL extraction or HEAD/Range probe fails, stop and fix source provenance instead of trying random archive links.

## Validation and limits

Offline tests verify notebook JSON, Python cell syntax, exact target/byte gates, source host filtering, ON-row parser, and default no-download state; they do **not** test Colab authentication, archive throughput, remote redirects, HDF5 readback, actual observations, RFI, or signal detection.

Next scientific gates: verify download URL/observation ID and HDF5 header time/frequency/polarization axes; create a bounded waterfall visualization; then add synthetic-tone recovery on **copies** and examine the on/off control cadence. No raw data or observations belong in GitHub, `main`, or Render. This is an engineering pilot, not an extraterrestrial detection.

Research ticket: https://github.com/gittenssexton/echolens-api/issues/16
