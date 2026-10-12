# EchoLens — GALAH DR4 canonical sources and acquisition rules (v1)

**Date:** 2026-10-12. **Scope:** provenance cleanup and source integration; **not** a completed experiment or a discovery claim. This document supersedes outdated *status summaries* but **does not overwrite** the actual dated experiment reports, source archives, or frozen P2B source-selection criteria.

## Canonical data roles

| Dataset | Canonical use | What it is *not* |
|---|---|---|
| Original GALAH DR4 `galah_dr4_allspec_240705.fits` | Authority for **per-observation** identifiers (`sobject_id`) and original-release stellar/quality measurements; can contain multiple spectra of one star | Not one independent star per row and **not** the observed spectrum pixel array |
| Original GALAH DR4 `galah_dr4_allstar_240705.fits` | **Recommended one-record-per-star** parameter/abundance reference; star-level cohort joins | Not every individual visit; don't use an allstar summary to erase repeated-observation metadata |
| Original `galah_dr4_vac_wise_tmass_gaiadr3_240705.fits` | Supplemental photometry, Gaia crossmatch and uncertainties where required | Not a substitute for `allspec` or a guaranteed artifact-free infrared detection |
| Official per-visit `single_fit_spectrum.fits` | Observed flux, quoted uncertainty, **in-sample fitted model**, GALAH fit-selection mask at the pipeline's fitted wavelength grid | Not the original eight-HDU HERMES camera reduction; do not treat `mob=True` as detector bad-pixel proof or fitted residuals as independent p-values |
| Original HERMES 1D camera FITS, one per arm | Eight-HDU reduced 1D observation: sky, telluric, relative error, scattered light, cross-talk, and HDU 7 native wavelength-dependent LSF FWHM | Not raw two-dimensional detector CCD; not always available for every arm/visit |
| Kos et al. 2025 *detrended* DR4 VizieR mirror | **Provisional** P2B cohort selection and engineering feasibility (preserve original provenance) | Not a byte-for-byte copy of the original 2024 GALAH release, so it cannot silently replace original-release confirmation |

**Naming precision:** Store Gaia DR3 IDs and GALAH `sobject_id` values as **exact decimal strings** or lossless signed 64-bit integers; never floating-point identifiers. Use (release, `sobject_id`) as visit identity and Gaia source ID as source-level independence key. Preserve every visit-to-source association, original source version, provenance and measured uncertainty. An unresolved join is quarantined, not guessed.

**Bulk download policy:** The linked full `allspec` (~832 MiB), `allstar` (~723 MiB) and Gaia/WISE value-added (~742 MiB) FITS releases are **available but have not been imported here**. Do not start multi-GB transfers to populate a two-star engineering registry. Use bounded, auditable queries or explicitly authorized targeted release extraction first. The two original-release Gaia-to-GALAH pairs have been verified against a CDS/VizieR mirror of the original Buder et al. GALAH DR4 **allspec** catalogue, with native subset response preserved and hashed. That does **not** mean the whole original survey table has been imported.

## Spectral retrieval (DR4, not DR3)

Use Data Central's GALAH DR4 Datalink service, with actual `sobject_id`:

- **Metadata discovery / original-file listing:** `https://datacentral.org.au/vo/slink/links?ID=<sobject_id>&DR=galah_dr4`
- **Request original camera FITS:** `https://datacentral.org.au/vo/slink/links?ID=<sobject_id>&DR=galah_dr4&FILT=B&RESPONSEFORMAT=fits` (and similarly G, R, I; **do not include `IDX`** for original files)
- `IDX=0` requests an **extracted product**, not an original eight-HDU FITS; the DR4 documentation includes an inherited example URL with `DR=galah_dr3`, which **must not be copied** for DR4 research.

Validate original bytes before admitting them to science storage: compare `GALAH_ID`/visit where present, `SPECTID` and camera number, wavelength WCS range, FITS **eight HDUs**, HDU 7 positive per-pixel resolution-profile FWHM, data completeness, independently calculated SHA-256 and source URL. Reject any mislabeled, duplicated, truncated, or cross-band file. Never relabel a returned infrared arm to green to satisfy a missing requested camera.

**Observed access issue (2026-10-12):** `FILT=B` and `FILT=R` original requests were valid eight-HDU products for each of two pilot stars. G and I requests were inconsistent with camera identities and were quarantined. Direct `services/sov/.../download` URLs exposed by Datalink metadata returned HTTP 403/500 on our runner; earlier *constructed* `cloud.../observations/...` paths returned HTTP 404. These are archival access/representation findings, not evidence that the star lacks green/infrared spectra. Another star's LSF must never be substituted for this star's missing camera.

## Registered two-source engineering evidence

- Original-release verified: `GaiaDR3 39909218369012608` ↔ `GALAH 151111003101245`; `GaiaDR3 4616578742686592` ↔ `GALAH 221003001101138`.
- **Four original camera spectra stored and hashed:** B and R for each star, with LSF median FWHM in Å (star 1: B 0.204011, R 0.284671; star 2: B 0.195564, R 0.280168).
- **Two** official per-visit `single_fit_spectrum.fits` saved separately (analyzed in SP01-P2B engineering only).
- **Four** arm records (G and I for each) explicitly quarantined because the returned native identity is not validated.
- Full original-file SHA-256, source links and clear status are in [`data/galah_dr4_source_registry_v1.json`](../data/galah_dr4_source_registry_v1.json). Original bytes, source-native response subset, analytical reports and failures remain archived at [EchoLens SP01-P2B Drive](https://drive.google.com/drive/folders/18gx5k2UII841FJiwFBxvdMGs3GxS35yA).
- No holdout stars were touched. Earlier 50-source manifest is **provisional** and **not** a validated false-alarm distribution. Zero technosignature claims.

## Reproduce and enforce

```bash
python -m unittest tests.test_galah_dr4_registry -v
python -m scripts.galah_dr4_registry \
  --registry data/galah_dr4_source_registry_v1.json \
  --report /tmp/galah_dr4_source_report.json
```

That validates **metadata** consistency only; the output states `original_file_checksums_verified_this_run: 0` unless copies of all six original archived FITS are supplied with `--original-files-dir`. The command then independently verifies all provided files' SHA-256 digests; it does **not** claim to verify the astrophysical model or line-spread profile numerics. A passing metadata report is explicitly **not** a science readiness gate.

### Operating rules

1. Keep original FITS in Drive with exact byte hash and original provider URL; do not commit binary science data to GitHub.
2. New observations require original-release Gaia-to-GALAH join verification before inclusion; records for one Gaia ID remain the same source-level split across visits.
3. Default retrieval scripts to **manual GitHub Actions dispatch**, not every branch push. Small local tests may run in ordinary CI. Never retry a 403 through authentication bypass.
4. Publish incomplete or failed retrievals with explicit status; do not delete dated experiment reports or override errors with successful labels.
5. Extend the native camera retrieval method only after solving G/I mapping with `SPECTID`, wavelength and distinct payload checks; until then model only the verified arm(s), with real measured LSF where available.

## Reference links

- GALAH DR4 catalogues: https://www.galah-survey.org/dr4/the_catalogues/
- GALAH DR4 spectra and HDU definitions: https://www.galah-survey.org/dr4/the_spectra/
- Data Central public catalogue directory: https://cloud.datacentral.org.au/teamdata/GALAH/public/GALAH_DR4/catalogs/
- Native Datalink proof: https://github.com/gittenssexton/echolens-api/actions/runs/38290183285
- Original CCD file recovery report: https://github.com/gittenssexton/echolens-api/blob/research/sp01-p2b-source-controls-20261012/reports/sp01_p2b/NATIVE_DATALINK_RECOVERY_2026-10-12.md
