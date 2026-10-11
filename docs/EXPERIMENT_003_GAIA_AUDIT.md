# Experiment 003G — exact Gaia source-link audit (preregistered amendment)

This transport and catalog-link validation extends Experiment 003 *without changing its 250 already-frozen LAMOST spectrum identities*. It is separate from a confirmatory astrometric crossmatch because the archived VizieR activity table supplies **fiber coordinates in a J2000 frame, not an observation epoch**. It is not valid to use J2000 as an assumed LAMOST observation date. The original LAMOST DR9 General Catalog MJD must be acquired before epoch-aware positional certification.

## Inputs — frozen before archive query
- Original 250 LAMOST spectra collected in [Experiment 003](EXPERIMENT_003.md) and preserved in run 38146071576, artifact 11704832150 and archived in the Echo Lens Drive folder (109,649 bytes).
- Frozen 250 original `GaiaDR3` values exactly as decimal identifiers (no floating-point ID conversion), no re-selection and no filtering based on a Gaia match.
- Query **NASA/IPAC IRSA's Gaia DR3 mirror** `gaia_dr3_source` through TAP `https://irsa.ipac.caltech.edu/TAP/sync`, with the 250 IDs in ten groups of 25. Request `SELECT TOP 100 * FROM gaia_dr3_source WHERE source_id IN (...) ORDER BY source_id ASC` for each group; reject TAP `ERROR`/`OVERFLOW`, unexpected row count, duplicated source IDs, IDs outside requested set, non-monotonic order and changed archive hashes. The `TOP 100`/MAXREC=100 bound is deliberately greater than 25 so missing/excess response rows remain detectable.
- Preserve original native VOTable bytes per batch, exact query, source release, retrieval time, all original field metadata and SHA-256.
- Do not require the original 10,000-source Gaia pilot's **random-index** or **class probability** restrictions; this is a different independent-spectroscopy-selected source cohort.

## Registered outputs
- Count exact Gaia DR3 ID re-queries resolved out of 250; number of complete astrometric (RA, Dec, pmra, pmdec, error fields) solutions; `ruwe`, parallax and band availability; duplicate/repeated published IDs.
- For all matched records, tabulate **angular separation between current Gaia DR3 reference-epoch coordinates and the published LAMOST fiber coordinates**, explicitly labeled **different/unknown epochs**, and apparent Gaia G difference from the paper's published Gaia G. These are diagnostic discrepancies, **not** confidence-rated matches.
- Report sources lacking Gaia records, missing proper motion, separation greater than 3" and Gaia-G difference greater than 0.5 mag as manual review flags. These are **not reasons to retroactively drop experiment 003 records**.
- The primary feasibility metric is fraction of published IDs resolvable in Gaia DR3. No minimum pass threshold is claimed before execution.
- Derived JSON must reproduce byte-for-byte from frozen original Gaia and LAMOST VOTable bytes. No repository/Render API mutation.

## Limitations
The link from LAMOST to Gaia may have been produced by a positional algorithm. An exact ID lookup proves the identifier exists in Gaia DR3, **not** that it correctly identifies a particular LAMOST spectrum. Epoch-correct propagation and positional/covariance validation require original individual LAMOST epoch and position uncertainty. No stellar astrophysical normality or technosignature probability is established here. The high-SNR, bright FGK selection persists; no universal control-group representation is claimed.
