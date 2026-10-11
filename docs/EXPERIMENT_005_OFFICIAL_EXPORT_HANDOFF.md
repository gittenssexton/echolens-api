# Official LAMOST DR9 v2.0 export handoff — EchoLens 005

The current instrument-offset hypothesis cannot be confirmed from VizieR or Gaia alone. The original public catalog page is reachable but its static HTML showed no CSV/FITS links, while official SQL/FTP entry points redirect to sign-in. No login bypass should be attempted.

## Access the documented official interface
Official [DR9 v2.0 low-resolution search](https://www.lamost.org/dr9/v2.0/search) provides an **Obsid Constraints** box accepting a list of observation IDs; [official catalog page](https://www.lamost.org/dr9/v2.0/catalogue) documents CSV/FITS downloads. Use an authorized account in the browser if prompted.

The exact, real **250 obsid** identifiers from the frozen Experiment 003 sample are in [Echo Lens Drive: 250 obsids.txt](https://drive.google.com/file/d/1sREcOqdeiH-E-2wvgfNf0pKm9xA2Lb6E/view?usp=drivesdk), UTF-8 text, 250 unique decimal IDs, byte SHA-256 `7268e28af1875b59271ab86eb7c10d3dfc41e951d47b524272b809eabc0942a3`.

Paste/upload the entire exact ID list into Obsid Constraints. If the interface supports selecting output fields, request these original LRS General Catalog fields at minimum:

```
obsid,obsdate,mjd,lmjd,ra,dec,ra_obs,dec_obs,offsets,offsets_v,gaia_source_id,fibertype
```

Do not discard spectra whose fields are null; do not filter out bright stars or known mismatches. Export native CSV/FITS (prefer FITS if preserving full data type, units, and uncertainties). Save the **original downloaded file unchanged** and its precise URL/release in the Echo Lens Drive root, then run the already prepared importer in `scripts/lamost_epoch_003h.py` against an explicitly documented CSV schema. If only FITS is available, a new validated FITS adapter is needed. Keep archive byte SHA-256 and retrieval timestamp.

**Minimum single-object test:** the known flagged LAMOST `obsid=655310123` (Gaia DR3 `876451818359869824`). Inspect `offsets`, `offsets_v`, `mjd`, `ra_obs`, `dec_obs`. If `offsets=true`, compare measured fiber coordinate displacement to `offsets_v`; match only after propagation of Gaia 2016 position to actual observation epoch.

## Validation gates after export
1. Match all 250 observation IDs exactly; handle absent IDs and duplications as explicit failures, not substitutions.
2. Verify observation date vs MJD, frame, offsets_v units and range, official provenance, and original magnitude.
3. Propagate the Gaia source with proper motion (including its uncertainties) to the observation epoch; evaluate the LAMOST fiber-point and Gaia match with a documented fiber offset uncertainty model.
4. Check neighboring Gaia DR3 sources and optical contamination; do not certify stellar IDs or ordinary-control labels solely from an offsets flag.

No research catalog record is invented to fill missing official data.
