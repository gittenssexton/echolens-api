# EchoLens Experiment 007 — LAMOST DR9 cross-survey identity conflict adjudication

**Registered 2026-10-11 before any new ESA DR8 or Gaia DR3 source-record query.** This is a *post-hoc provenance investigation* triggered by Experiment 006B. It is not a blinded experiment, new search for technosignatures or classification of stars as ordinary.

## Frozen real-data evidence
- 250 genuine Huang et al. (2024) LAMOST DR9 VizieR `obsid` spectra, frozen 003 result raw JSON SHA-256 `efc4f3eaf5f5e1df8b60aa1897ffd93d44c3b05fe69318b27d3769fddb342e51`.
- Original 003G Gaia DR3 exact-identifier audit result SHA-256 `d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748`.
- Frozen 006B ESA DR9 LRS original 10 raw TAP VOTables + derived 250-outcome `results.json`, currently archived in Echo Lens Drive [here](https://drive.google.com/file/d/1GZcNqYW5CnIIGjFTr1DAva3-gUmzw2vg/view?usp=drivesdk). The VizieR and ESA archive release identity is **not** assumed identical.
- ESA LRS DR9 results: 241/250 found, 238 Gaia source IDs concordant, **2 different valid IDs**, **1 invalid sentinel `-9999`**, 9 unrepresented obsids. Do not change historical results.
- The flagged `obsid=655310123` has **ESA `offsets=1`, `offsets_v=4.89"`, fiber separation 4.8853", MJD 58189**. Its catalog offset is instrumentally explained; lack of ESA Gaia ID is *only a separate source-crossmatch provenance question*.

## Frozen investigation sets
**Two disagreement obsids, exact published ID pairs:**
- `235608062`: VizieR+003G Gaia DR3 `1215223960901067520`; ESA LAMOST DR9 `1215223960901067648`.
- `844313076`: VizieR+003G Gaia DR3 `2682701860879616256`; ESA LAMOST DR9 `2682701860880020992`.

**Nine absent from ESA DR9 mirror (preserve all):**
`52606232`, `257813193`, `318809041`, `447016213`, `458106245`, `459815059`, `475114198`, `570209101`, `574314070`.

## External data queries, decided before execution
1. Query a **single exact-ID Gaia DR3 TAP retrieval** from NASA/IPAC IRSA `gaia_dr3_source` for the four *different* decimal source IDs above, using a field list `source_id, ra, dec, ref_epoch, pmra, pmdec, pmra_error, pmdec_error, parallax, parallax_error, phot_g_mean_mag, phot_g_mean_flux_error, bp_rp, ruwe, duplicated_source, non_single_star`. `SELECT TOP 100 ... WHERE source_id IN (four ids) ORDER BY source_id`, `MAXREC=101`. Preserve all missing IDs rather than claiming false conflict resolution. Preserve full raw VOTable bytes, field metadata, request UTC, SHA-256 and numeric uncertainties; no Gaia ID may pass through floating-point conversion.
2. Query public ESASky **LAMOST DR8 low-resolution General** exact `obsid` membership for the *nine absent DR9* obsids. This is **release coverage research only**. A hit in DR8 is not a DR9 v2 confirmation or replacement. Source table `catalogues.mv_lamost_dr8_lrs_fdw`, discovered in 006A raw TAP schema. Retrieve `obsid, obsdate, mjd, ra, dec, ra_obs, dec_obs, offsets, offsets_v, gaia_source_id`, `TOP 100`, maxrec 101. Preserve missing observations, exact bytes, original published fields and TAP status.
3. **No broad searches** or sky-radius reassociation in this experiment. Avoid winner-takes-nearest; both identifier alternatives remain on record even if one is geometrically closer.

## Preregistered derived diagnostics
- Report source existence, no missing/unrequested/duplicate invalid results and exact source ID strings.
- For both conflicting obsids compute **Gaia 2016.0 reference sky position to ESA LAMOST observed fiber position** angular distance and to ESA **input target (`ra,dec`)**; compare with the original archived Gaia record; report **Gaia-G difference** if available and Gaia `ruwe`, PM availability, positional uncertainties and parallax. For nonoffset sources, compare to input target.
- Compute *descriptive* Gaia propagation using PM to ESA `mjd` using ICRS tangent-plane approximation with cos(dec) correction, compare differences before/after. This is **not full covariance+parallax astrometry, not identity adjudication**. Missing PM must be explicit.
- For nine absent obsids, report DR8 presence/count and raw fields if found, but never silently attach DR8 measurements to DR9 sources.
- For `655310123`, preserve ESA missing Gaia source ID; do not invent an alternate ESA identifier.
- Post-hoc review categories: `both_gaia_ids_present`, `one_or_both_gaia_ids_unresolved`, `ESA_missing`, `DR8_release_coverage`, `needs_independent_astrometric_confirmation`. No per-star technology scores or ordinary labels.

## Reproducibility and acceptance
Original frozen 006B archive is restored from GitHub Actions run `38152809325` artifact `echolens-esasky-006b-real-obsids`, with original VOTable response hashes. Original LAMOST and Gaia audit archives from runs `38146071576` and `38146667656`. All inputs, exact requests, original XML, manifest and deterministic JSON will be independently replayed twice offline byte-for-byte. No live Render, production SQLite, main, WISE data or earlier registered results modified.

Data documentation: ESA ESASky LRS DR8 & DR9 `https://sky.esa.int/esasky-tap/tap`; NASA/IPAC `https://irsa.ipac.caltech.edu/TAP/sync`; LAMOST original `https://www.lamost.org/dr9/v2.0/doc/lr-data-production-description`.
