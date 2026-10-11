# Experiment 004 — Gaia neighborhood and ambiguity pilot (prospective engineering protocol)

**Frozen 2026-10-11 before retrieving Gaia neighbors.** This is a *post-hoc follow-up* to the known 5.12 arcsecond Experiment 003G/003H discrepancy, plus a hash-selected control set. No claim of blinding, anomalous electromagnetism or extraterrestrial activity is made.

## Question
Could confusion among nearby Gaia DR3 objects contribute to the published LAMOST DR9–Gaia identifiers? Specifically: around the 2016-position of the highlighted LAMOST activity-catalog entry (`obsid=655310123`, published Gaia DR3 `876451818359869824`), is any *other* Gaia DR3 source closer to the catalog `RAJ2000/DEJ2000` coordinate than the published Gaia ID? How frequently do alternatives arise in a 24-object, deliberately *non-representative* reproducible comparison sample?

**Crucial caveat:** J2000 catalog coordinates are not verified actual fiber pointing and the date of observation is unknown; closest geometric source is *not* a certified counterpart. The result describes crossmatch **ambiguity triage only**.

## Frozen 25-source selection
Use the exact 250 original LAMOST DR9/Huang+ 2024 records from Experiment 003, and the existing Experiment 003G Gaia archive, each restored from immutable GitHub Actions artifacts with original request hashes. Do not re-fetch their observations.

1. Include the previously identified flagged `obsid=655310123`.
2. From the other 249 LAMOST `obsid` strings, order by `SHA256("echolens-004-v1:"+obsid)`, with numeric ID tiebreak. Take the first **24**; use exactly those, with no subsequent substitutions.
3. Preserve target obsid, source Gaia DR3 ID, VizieR `RAJ2000/DEJ2000`, catalog G magnitude, original Gaia reference epoch, program/protocol SHA and both input JSON SHA-256 values in the frozen selection.
4. Write the frozen list before querying any Gaia neighborhood. Reject any change on rerun.

## Gaia neighborhood observation acquisition
Query **Gaia DR3** as served by NASA/IPAC IRSA, table `gaia_dr3_source`, endpoint `https://irsa.ipac.caltech.edu/TAP/sync`. Submit exactly **one cone per query** centered on each archived VizieR catalog coordinate, radius **12 arcsec**. Format VOTable; `SELECT TOP 1000 source_id, ra, dec, ref_epoch, pmra, pmdec, ra_error, dec_error, pmra_error, pmdec_error, parallax, parallax_error, phot_g_mean_mag, phot_g_mean_flux_error, ruwe, duplicated_source, non_single_star FROM gaia_dr3_source WHERE 1=CONTAINS(POINT('ICRS',ra,dec),CIRCLE('ICRS',<RA>,<Dec>,0.0033333333333333335)) ORDER BY source_id ASC`. (Software shall format exact coordinate literals from snapshot, not the placeholder strings in this description.)

Enforce `QUERY_STATUS=OK`, reject `OVERFLOW`, unexpected schema/field metadata, duplicate/non-decimal 64-bit Gaia IDs, invalid coordinates/negative reported uncertainties, or 1000 rows indicative of a cap. Save **original XML responses**, query URLs or parameters, retrieval UTC, HTTP metadata, SHA-256 checksums, field metadata and all candidate records. Failed or empty cones must remain explicit. No automatic search-radius enlargement or substituted target.

## Deterministic result
For each target, report all nearby DR3 sources within 12", with:
- catalog-coordinate separation at Gaia reference epoch (display 0.0001 arcsec, eligibility uses full unrounded separation);
- whether the *published* Gaia ID is present, its angular offset, and whether another source is strictly closer;
- nearest/second-nearest distance and magnitude differences where available;
- density of additional candidate neighbors within 1", 3", 6" and 12";
- missing PM/error flags and current inability to make observation-epoch-qualified posterior identity claims.

Classify each target only as `published_id_nearest`, `published_id_not_nearest`, or `published_id_absent_in_12_arcsec_cone`. A nearer Gaia source is a **review flag**, never proof of misassociation. Preserve raw catalog measurements and published uncertainties; input and output hashes are mandatory. Two offline replays must generate byte-identical output JSON.

## Scientific limits and next gate
This experiment is deliberately targeted at a previously seen failure plus 24 hash controls, so its rates are **not** population-level prevalence. It cannot establish valid/invalid associations, explain fiber offsets, or conclude technology. LAMOST DR9 v2 LRS General observing dates, `mjd`, `ra_obs/dec_obs` and deliberate fiber offsets remain essential. Subsequent epoch-propagation/covariance assessment must be a separately frozen protocol and should inspect background neighbors before promoting sources to controls.

LAMOST DR9 v2 original catalog documentation: https://www.lamost.org/dr9/v2.0/doc/lr-data-production-description
Gaia DR3 original source documentation: https://gea.esac.esa.int/archive/documentation/GDR3/Gaia_archive/chap_datamodel/sec_dm_main_source_catalogue/ssec_dm_gaia_source.html
