# EchoLens project checkpoint v13 — 2026-10-13

## Results

Completed three next steps: acquired real Gaia neighborhood evidence for the nine fixed infrared development stars; located and validated real TESS Sector 32 light-curve and pixel observations for TIC 4206066; computed and documented cross-project statistical feasibility gates. No reserved infrared stars were scored, no transit search was performed, and no candidate significance or control certification was assigned. Main and Render remain unchanged.

## Infrared development neighborhoods

The nine targets and 60-arcsec cone size were frozen before the requests. All original Gaia VOTables, 17-field schemas/units, exact queries, timestamps and hashes are retained. Each response has QUERY_STATUS=OK, includes its exact target once, has unique source IDs, and stays below the 200-row limit. Counts refer only to sources in those finite Gaia cones.

| Target Gaia DR3 ID | Cone rows including target | Nearest neighbor with complete PM at W3 epoch (arcsec) | Within 8.25 arcsec, complete PM | Neighbors without PM | W3 aperture flag |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2759006524739613056 | 3 | unresolved | 0 | 2 | 0 |
| 3075599868480948992 | 11 | 17.6145 | 0 | 0 | 0 |
| 2433664848010750848 | 4 | 45.6947 | 0 | 2 | 1 |
| 2984872253470024576 | 7 | 22.3647 | 0 | 1 | 1 |
| 1742112230738093312 | 16 | 6.6238 | 1 | 0 | 0 |
| 2336863054027651456 | 5 | 21.0473 | 0 | 0 | 0 |
| 6669301637583655168 | 17 | 10.9491 | 0 | 2 | 0 |
| 2151835210082468992 | 11 | 30.2662 | 0 | 0 | 1 |
| 3657301580397050240 | 2 | 37.2362 | 0 | 0 | 1 |

Total Gaia cone records: 76, including nine targets. Seven non-target rows lack proper motion, across four fields; they remain unresolved at the WISE epoch rather than being treated as absent. Linear tangent-plane proper motion propagates both targets and complete-motion neighbors to the target W3 mean MJD; the reported MJD uses the WISE column convention approximately and is not an error-calibrated astrometric model. Parallax, perspective acceleration, complete covariance, close-source catalog completeness and sources moving into the cone are not modeled.

Target 1742112230738093312 has neighbor 1742112230742235392 at 6.6238 arcsec at the approximate W3 epoch, G=18.9343, inside the standard 8.25-arcsec aperture despite catalog aperture flag zero. Target 6669301637583655168 has a complete-motion neighbor at 10.9491 arcsec, inside 15 arcsec. No complete-motion neighbor is within 6 arcsec for these fields. Optical G magnitudes are not converted into W3 flux contamination; red/dusty sources and unresolved blends are not excluded by this screen. Four previous catalog W3 confusion flags remain unchanged even where Gaia does not show a complete-motion source inside the aperture. No star was dropped or replaced.

## TESS real-data readiness for H09 / TV01-B

The exact-target MAST CAOM query returns one public SPOC time-series observation: tess2020324010417-s0032-0000000004206066-0200-s, observation ID 28151492, Sector 32. Its native light curve is 1,903,680 bytes and pixel file 45,889,920 bytes. Download URLs derive from returned product dataURIs; byte counts match the provider metadata. FITS verification, TICID=4206066 and SECTOR=32 checks pass. This exact-target query is not an exhaustive inventory of community products or FFI observations.

A separate documented TESSCut coordinate sector query reports FFI coverage in Sectors 6, 32 and 98. Only Sector 32 native SPOC files were acquired in this run; FFI-derived files for 6/98 and future-sector pixels were not downloaded. FFI coverage does not assert that every time stamp or usable target flux exists.

Both Sector 32 products contain 18,730 cadences. Cadence IDs match exactly, TIME arrays agree to 1e-12 day including matching missing values, and aperture masks match exactly. Native clock is TDB, solar-system reference, TIME in days plus BJDREFI=2457000 and BJDREFF=0. There are 18,011 finite times and 17,094 quality-zero rows with finite positive PDCSAP errors. Retained span is 25.8114 days; median spacing 120.0015 seconds. TPF flux has shape 18730×11×11. Native quality values and all column units/errors are retained.

The median quoted fractional PDCSAP error is 0.000839801 (~840 ppm per cadence). This is a descriptive pipeline formal error, not a transit detection limit or independent white-noise estimate. The displayed light curve is only median-normalized and is not further detrended. No period, phase, transit depth, centroid veto or planet/technosignature inference was fitted. SAP/PDCSAP comparisons, time-correlated noise, injection/recovery and independent pixel-level false-positive checks remain required. Existing candidate knowledge makes archival work retrospective.

## Statistical and workflow requirements

The companion STATISTICAL_GATE_AMENDMENT_PROPOSED.md records mathematical corrections and proposed run gates. It preserves current protocols and is not independent scientific ratification. Numerical feasibility checks are generated in statistical_gate_checks.json.

For conservative empirical rank p=(1+#null >= score)/(N+1), the smallest possible p is 1/(N+1) under the registered valid null/exchangeability assumptions. At a single 1% threshold at least 99 null scores are needed merely for resolution; three Bonferroni-adjusted folds need at least 299; 100 tests at a 1% family threshold need 9,999; the first-ranked BH threshold q/m=1e-6 for 10,000 tests needs 999,999. These are rank-grid resolution requirements, not sufficient calibration and not mandatory million-star observing programs: a different validated tail or joint-null method could be justified separately. Bootstrap repetitions on one star are not independent astrophysical controls.

MR01 currently describes combined p as the raw product of optical and radio p-values. That product is a statistic, not generally a calibrated p-value. Even for independent continuous uniform p-values, two values of 0.001 give raw product 1e-6 but Fisher combined p≈1.481551e-5. For real overlapping, selected or correlated surveys the required assumptions are unverified; finite discrete empirical p-values also need appropriate calibration. Cross-survey combination must be developed using a joint null or a separately justified method, without assigning a numerical significance from the current placeholder.

Next dependency order: (1) freeze retrospective Sector 32 processing/injection criteria and control selection before event scoring; (2) acquire and check native FFI cutouts for S6/S98 for cross-sector recovery; (3) quantify infrared contaminant flux/PSF/background effects and predictive uncertainty on development data; (4) validate source-level null calibration before reserved tests or cross-survey combination. General truncated LAMOST catalogs and unavailable GALAH cameras remain external acquisition blockers.

## Verification and replay

24 local tests pass, including four new checks for unresolved missing motion, RA wrap, altered native bytes and reserved-role rejection. Neighborhood, TESS inventory and native QA JSON outputs replay byte-identically with network sockets blocked. The archive carries frozen designs, exact input JSONs, native Gaia/TESS responses, acquisition manifests, scripts/tests and outputs. Run python -m scripts.project_checkpoint_v13 replay and python -m scripts.project_checkpoint_v13 tess_QA from the extracted project root with requirements-nir.txt installed. No fresh acquisition is needed for replay.

Primary documentation:
- MAST API services: https://mast.stsci.edu/api/v0/_services.html
- NASA TESS native data and uncertainties: https://heasarc.gsfc.nasa.gov/docs/tess/data-products.html
- TESSCut sector API: https://mast.stsci.edu/tesscut/
- Independent/continuous p-value combination assumptions: https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.combine_pvalues.html
