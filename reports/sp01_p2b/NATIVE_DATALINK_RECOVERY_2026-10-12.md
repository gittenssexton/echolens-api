# EchoLens SP01-P2B: original GALAH DR4 native camera retrieval — October 12, 2026

## Result
**Four native 8-extension GALAH 1D reduced-camera spectra recovered from official Data Central Datalink, with instrument-specific resolution profiles.** Two previously exposed calibration stars only; no holdout or astronomical anomaly scoring.

## Underlying problem and retrieval method
The GALAH public cloud root lists only catalogs and analysis products, not the old `observations/` path. That guessed path returned HTTP 404. Data Central documents that Datalink requests without `IDX` return original spectra and queries with `IDX=0` return simplified extracts. On the live Github Actions runner, requests through `/vo/slink/links?ID=<sobject>&DR=galah_dr4&FILT=<band>&RESPONSEFORMAT=fits` produced native FITS for B and R. This is confirmed by 8 HDUs and HDU 7 measured `resolution_profile`.

### Source and LSF measurements
| GALAH observation | Camera | Original FITS SHA-256 | Median FWHM (Å) | Median λ/FWHM |
|---|---|---|---:|---:|
| `151111003101245` | B | `daea235a3d7409ce4b8b02cac8277d171dc7db5e81787cbbd6461758cf18d566` | 0.204011 | 23,755.4 |
| `151111003101245` | R | `488db4045d9716527c0836abf6882166aeb248974bdcc896ab98f78db2fcd79f` | 0.284671 | 23,212.8 |
| `221003001101138` | B | `dd08bdf7b6925342732a12cffee31808954aab16575db397498c65c3fc08c153` | 0.195564 | 24,587.5 |
| `221003001101138` | R | `f8e7710f8d23bc311f87e0c6488d6174e7617c5620d5cedace812ddacabcae5f` | 0.280168 | 23,661.7 |

## Remaining limitations
- Datalink requests with `FILT=G` or `FILT=I` gave FITS responses that failed source-camera SPECTID checks. These responses had the same SHA per star for both bands, so must not be accepted as unique green/IR observations.
- The unfiltered original Datalink metadata *does* list four exact combined-camera file links and additional exposures (16 links per star). Direct calls to `services/sov/.../download/...fits` returned HTTP 403 (one HTTP 500). The direct URLs cannot be assumed publicly downloadable from the Actions runner; Datalink remains the working original-delivery proxy.
- Investigate whether the correct green filter is `V`, not `G`, based on Data Central documentation; do not relabel a wrong FITS as green. Keep all rejected URLs and SHA in the JSON audit.
- This observation only establishes native LSF and valid FITS schema. Original Gaia source identities were separately validated against Buder+2025 DR4; neither star yet has an independently calibrated false alarm rate.
- No changes to `main`, production Render, or the 20 holdout stars.

## Reproduce / verify
Datalink documentation: https://docs.datacentral.org.au/reference/services/simple-spectral-access-ssa-service/
GALAH spectra documentation: https://www.galah-survey.org/dr4/the_spectra/
GitHub validated workflow: https://github.com/gittenssexton/echolens-api/actions/runs/38290183285
Source JSON: `datalink_results.json`; source XML: `_datalink_listing.xml`; native original FITS: `_original_camera.fits`.
