# First visual review of five survey counterparts

Date: 2026-10-11. Reviewer: Codex assisted visual inspection of the generated 20-panel montage. This is a preliminary qualitative review, not independent human confirmation or quantitative contamination measurement.

All five fields were inspected in native AllWISE W1/W3 and 2MASS J/Ks cutouts, each approximately 90 arcsec wide. The cyan marker is Gaia propagated to the survey epoch; the red marker is the stationary catalog position. Markers overlap at this display scale; that does not validate sub-arcsecond astrometry. Orange markers show other retrieved catalog objects within the original 15-arcsec cone. Objects beyond that cone are visible but are not exhaustively cataloged here.

| Gaia source ID | Visual finding | Consequence |
|---|---|---|
| 4310899120739084800 | Central source is visible in all four panels. Several nearby sources and strong W3 background/neighbor structure are visible. 2MASS alternatives occur at 6.83 and 8.76 arcsec. | Model blending/background before attributing W3 flux; Gaia extinction estimate also needs checking. |
| 4461930649238469760 | Central source is visible and relatively isolated in these cutouts. W3 background is noisy; no obvious overlapping bright source is apparent in the display. | Best starting field for development of the photosphere-fitting workflow, conditional on further quantitative checks. This does not certify an ordinary-star control. |
| 2224020313110506496 | A compact W1 source is present, but the W3 field has complicated background/neighbor structure and is less clearly isolated at the marked position. | Defer W3 interpretation pending background/PSF review, positional-convention resolution and extinction modeling. |
| 192355921445905536 | The central near-infrared source is visible; several surrounding sources and a low-contrast, structured W3 field are apparent. | Retain the W1 H artifact flag and review W3 independently. Display inspection cannot clear the catalog flag. |
| 4262211057903494912 | A bright central source is present across bands, with nearby objects resolved in 2MASS. | Treat as variability/contamination development case; saturated W1/W2 and noncontemporaneous photometry prevent ordinary-control use without a separate model. |

Image intensities use independent percentile/asinh display stretches. They are not calibrated cross-band flux comparisons. No centroid fitting, aperture photometry, PSF subtraction, uncertainty-image analysis or single-exposure review was performed. Unresolved binaries, diffuse emission and color-dependent neighbors can remain even when a panel appears isolated.

Original FITS cutouts, response hashes and image-discovery metadata are archived. 2MASS images were selected by the exact catalog coadd_key and band; AllWISE images use the catalog coadd_id. The catalog's internal 2MASS association key agrees with our selected 2MASS record in all five cases. That is a catalog consistency check, not independent identity confirmation.
