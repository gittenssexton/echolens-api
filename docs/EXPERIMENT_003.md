# EchoLens Experiment 003 — independently measured stellar reference candidates (preregistration v1)

**Status:** protocol frozen before any LAMOST acquisition or analysis. This is a survey feasibility and provenance pilot, not a technosignature hypothesis test.

## Scientific question and design
Can EchoLens reproducibly retrieve a fixed sample of **250 real LAMOST DR9 low-resolution spectra** with independent spectroscopic stellar-parameter estimates (Teff, logg, [Fe/H]), associated uncertainties, activity indicators, observation IDs and published Gaia DR3 links, without mutating the Gaia registry or assigning premature clean-control labels?

### Source and target population
- Independent dataset: Huang et al. 2024, *ApJS* 272, 6, Ca II infrared-triplet stellar-activity library based on **LAMOST DR9**, distributed as VizieR table **`"J/ApJS/272/6/catalog"`**, 699,348 **spectra**, representing 562,863 **FGK stars**, already selected for SNR >100.
- Source ReadMe and units: https://cdsarc.cds.unistra.fr/viz-bin/ReadMe/J/ApJS/272/6?format=html&tex=true
- Query service: IVOA TAP VizieR synchronous endpoint `https://tapvizier.cds.unistra.fr/TAPVizieR/tap/sync`. Archive the exact ADQL/HTTP request, unmodified response bytes, SHA-256, field units/descriptions, retrieval UTC and VizieR source citation.
- Sampling frame: VizieR-created `recno` values 1 through 699348, **not physical identities**. This assumes a contiguous row-number range and is verified at acquisition. Select 250 unique recno integers in [1,699348] with SHA-256 rejection sampling: iterate counters 0,1,2,... and compute `int(SHA256("echolens-003-v1:" + decimal_counter),16) % 699348 + 1`; accept first 250 unique indices, then sort ascending. Record all selected row numbers and their hash; no filtering or replacement of failed entries.
- Retrieve in 10 batches of 25 `recno IN (...)`, sorted numerically. Query `SELECT *` to retain all native published fields; reject failed/overflow TAP response, missing/duplicated recno, unexpected row count, mismatched fields, extra/unrequested rows and any changed acquisition hash.

## Quality classification — measurements versus inferences
For **each individual spectrum** preserve the original published `obsid`, `GaiaDR3`, `SNRi`, `SNRz`, `RAJ2000`, `DEJ2000`, `Teff`, `e_Teff`, `logg`, `e_logg`, `FeH`, `e_FeH`, and Ca II activity R/R+ indices, original units and nulls. Catalog Teff/logg/[Fe/H] are **spectroscopic pipeline inferences derived from independently collected LAMOST spectra**, not direct line counts and not an EchoLens AI interpretation.

A record is *spectroscopic-label-ready* only if it has a nonzero decimal Gaia DR3 ID (exactly string-preserved); unique LAMOST `obsid`; finite Teff in [4800,6800] K, logg in [3.6,4.9] (log cm/s2), FeH in [-1.01,0.51] dex, and finite strictly positive `e_Teff`, `e_logg`, `e_FeH`, plus SNRi>=100 and SNRz>=100. These are operational suitability gates for this published specialized catalog, **not universal stellar-physics limits**. Sentinels -9999, blank or NaN always become null and incur a recorded quality failure; zero errors are not accepted as perfect certainty. Keep rejected records and reasons rather than silently filtering.

Multiple `obsid` may map to a single Gaia DR3 ID; preserve every spectrum, counts and separate uncertainties, do not double-count a star. The paper's built-in Gaia association is a **provisional published crossmatch** only, not a newly confirmed identity. True Gaia identity must be rechecked with archive astrometry, positional covariance and epoch before certification.

## Primary preregistered outputs
- Exactly 250 requested and retrieved VizieR row numbers; no invented or replaced records.
- Count of non-null unique Gaia DR3 identifiers, repeated-spectra identities, passed spectroscopic-label-ready records and distinct passed stars; explicit quality-failure counts.
- Count of Gaia IDs overlapping the frozen initial 10,000-source Gaia DR3 sample, **including zero**. The 10k classification-selected pilot is tiny compared with the >billion-source Gaia parent, and overlap must not be presumed.
- Histograms/percentiles of externally inferred Teff, logg, FeH and uncertainties; survey sky/brightness coverage and gaps; complete provenance, raw response fingerprints and a reproducible offline replay.
- A reproducibility **pass** requires the same inputs and byte-identical output JSON from two offline replays. A science **pass** or claim of valid matched controls is not defined: a pilot can reveal very few confirmed links or unsuitable coverage.

## Cautions and next gate
- This high-SNR spectroscopic FGK dataset **cannot** stand in for faint Gaia sources, white dwarfs, M stars, giants, known binaries, or other absent populations. Do not call these 250 *clean controls* or *ordinary stars* before independently validating astrophysical status. A paper on stellar activity includes stars with real activity, binaries and complex astrophysics; high activity is not technology evidence.
- VizieR `recno` is an ingestion convenience, not a stable astrophysical source ID. Changing VizieR catalog versions requires a NEW manifest/protocol, never silent replacement.
- The LAMOST authors' Gaia identifier joins likely use positional matching. No individual link can be approved without quality-controlled Gaia astrometry and survey epoch handling.
- New spectroscopic observations and results are stored **outside** `data/registry.sqlite3`; no live API/Render, WISE interpretation, anomaly score, FDR or AI-origin probability is touched.

Data sources: Huang et al., 2024 (2024ApJS..272....6H), original LAMOST DR9 optical spectra; ESA Gaia DR3; VizieR / CDS presentation.
