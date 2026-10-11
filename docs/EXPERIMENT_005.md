# Experiment 005 — published fiber-coordinate offset versus brightness; official epoch-metadata gate

Status: **post-hoc feasibility analysis**, not an anomaly/technosignature experiment or a pre-registered discovery claim. On 2026-10-11, the 5.1201" LAMOST-to-Gaia separation and source brightness G≈9.45 were already known. The suspicion of **deliberate fiber offset to avoid saturation** was formed after seeing that source. All comparisons are descriptive and exploratory.

## Scientific question
Could a deliberate bright-source fiber offset (explicitly documented in official LAMOST DR9 LRS documentation) plausibly explain the earlier 5.1201" difference between the Huang et al. 2024 VizieR tabulated `RAJ2000,DEJ2000` and the published Gaia DR3 source? The Huang catalog explicitly describes its coordinates as *RA/Dec of fiber point (J2000)*, but the individual observation epoch and the DR9 `offsets`, `offsets_v` flags are not yet in our archived source observations. **Only an authentic `obsid=655310123` row or matching spectrum FITS header from LAMOST DR9 v2.0 can confirm an instrumental offset**.

Official documentation:
- https://www.lamost.org/dr9/v2.0/doc/lr-data-production-description
- https://www.lamost.org/dr9/v2.0/doc/faq
- https://www.lamost.org/dr9/v2.0/catalogue
- VizieR original Huang+ 2024 ReadMe: https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/J/ApJS/272/6?format=html&tex=true

## Frozen original observations
Use **unchanged**, previously verified files:
- Experiment 003 original `results.json` (250 actual published LAMOST spectra), SHA-256 `efc4f3eaf5f5e1df8b60aa1897ffd93d44c3b05fe69318b27d3769fddb342e51`;
- Experiment 003G `results.json` (250 exact published Gaia DR3 IDs and archive records), SHA-256 `d11e0c62eaa8aa26b2fe92fc30b0ca93891459caf4878d89cf2285fc0527a748`.
All 250 `obsid` and Gaia identifiers must match 1:1. No target replacement; no new Gaia astrometry or model-inferred observation dates.

## Fixed descriptive outputs
1. Preserve every original source, exact `obsid`, published Gaia source ID, RA/Dec of catalog fiber, Gaia 2016 epoch coordinates, G magnitude and uncorrected separation.
2. Two predefined descriptive brightness partitions: `G < 11` versus `G >= 11` and `G < 10` versus `G >= 10`. Report denominators, median/p90 separation, count with separation >1" and >3". Null values excluded only from the affected bin with reported reasons. Do not reinterpret the bin threshold as a scientific cutoff for saturation.
3. Rank the 5.1201"-offset source by observed G brightness (1 = brightest) and by uncorrected separation (1 = largest) among the 250, plus all other >1" offsets and published proper motion availability.
4. Compute Spearman rank correlation of G magnitude with raw positional offset for descriptive sensitivity and report source count. This is *observational exploratory characterization*, not a blinded p-value, not a model of instrument offsets, and not proof of saturation.
5. Produce a reproducible offline JSON, with source & protocol hashes; optionally make a graph explicitly labeling Gaia 2016 vs unknown LAMOST fiber observing epoch.

## Actual epoch-based verification remains a separate gate
Only accept an **official LAMOST DR9 v2.0 LRS General/Input catalog CSV or FITS export or original spectrum FITS header** with exact `obsid`, observation `mjd/obsdate`, `ra_obs/dec_obs`, `offsets`, `offsets_v` and source/URL/byte SHA-256. Note the VizieR coordinates are labeled fiber-point coordinates; their epoch interpretation must still be inspected. The official [catalog page](https://www.lamost.org/dr9/v2.0/catalogue) documents downloadable CSV/FITS products; the official SQL Query and FTP routes redirect to authentication in the current public browsing environment. Attempt access only through documented official public pages/links, with no invented private API or authentication bypass.

The existing `scripts/lamost_epoch_003h.py` has an explicit official-CSV reader; preserve its strict input policies, add unit tests if a real official export is obtained, then implement Gaia proper-motion propagation and error accounting. No crossmatch shall be certified or discarded from data currently held.

## Interpretations excluded
No confirmation of offsets without `offsets`/FITS `OFFSET`. Large raw separation not evidence of technology or false association. No population-level prevalence, controlled astrophysical comparison, discovery score, or causal claim. All code stays in development and leaves `main`, Render, production registry untouched.
