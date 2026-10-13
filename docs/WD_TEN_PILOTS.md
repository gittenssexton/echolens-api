# Ten sequential WD observational pilots — 2026-10-13

Ten linked exploratory analyses executed in strict P01→P10 order. They share
inputs and are not ten independent replications or confirmatory discovery tests.
The primary ten-source cohort was already development-exposed in CP001. All
reported-source associations remain provisional and no ordinary controls or
physical excesses are certified. Main and Render are unchanged.

| ID | Experiment/question | Observed outcome |
| --- | --- | --- |
| P01 | Does proper motion materially change fiber separation? | 3/10 changes at least 0.1 arcsec. |
| P02 | Is neighbor ambiguity aperture dependent? | All ten single within 2–3 arcsec; one gains a second candidate at 6 arcsec. |
| P03 | Does Gaia astrometry meet the pilot quality screen? | 10/10 pass the frozen screen; this is not physical-source certification. |
| P04 | Are repeated WD parameter estimates consistent at formal-error precision? | Supplemental 10 reported IDs, 26 observations, 46 parameter comparisons; 30 conservative formal-error tension flags. |
| P05 | Is AllWISE coverage positionally unambiguous under epoch sensitivity? | 8/10 unique provisional central-epoch candidates. |
| P06 | Which WISE bands retain clean detections and errors? | W1: 7; W2: 3; W3/W4: 0 clean detections. Upper limits retained. |
| P07 | Are clean W1−W2 colors distinguishable from zero reference? | Three measured colors; no conservative three-sigma zero-reference flag. |
| P08 | Is 2MASS association unique using native JD? | 5/10 provisional matches. JD-to-TCB propagation assumes UTC for native JD. |
| P09 | Which near-infrared colors have clean JHK measurements? | Four clean JHK cases; native errors and correlation bounds preserved. |
| P10 | How many cases support later five-band modeling? | Three technical passes; zero authorized excess searches pending identity/image/model/control gates. |

## Amendment and failed attempts

Initial design frozen at f17edbd04970cf1b77faf06b30f67c8b1f1e12c4 before new
infrared acquisitions. Original primary P04 has no repeat observations, so its
question was not testable. Preserve that result. A separate ten-ID repeat
supplement was selected by availability, positive formal uncertainties and fixed
hash ranking, without selecting by measured differences; amendment frozen at
535636379a5c1928d75ae0ded8b6fe50bb1f0c83 before comparisons. No other experiment
changed its primary cohort or threshold. The supplement is exploratory,
not a retrospectively claimed preregistered discovery sample.

Two combined-cone acquisition attempts failed IRSA query parsing. Existing
EchoLens IRSA code documents the single-geometric-constraint restriction.
Transport was corrected to one cone per request; twenty successful complete
VOTables preserve all native fields/uncertainties, queries, timestamps and
checksums. Failed originals remain in the evidence package. The first two
attempts' P10 zero-readiness outputs lacked upstream observations and are
explicitly superseded, never scientific zero results. A regression test now
prevents a missing upstream acquisition becoming a readiness verdict.

`execution_003/raw` contains successful acquisitions. `execution_004` is the
authoritative amended sequence. Verification replay exactly reproduced every
scientific result payload with socket connections blocked. Timestamps prove
one analysis finished before the next began. Tests check upper-limit exclusion,
contamination, covariance bounds, dependency failure and single-cone transport.

## Interpretation and next gate

The 30/46 repeat-fit flags involve correlated pairwise comparisons within just
ten reported IDs. They compare survey fitted estimates with formal quoted
errors; shared modeling/calibration systematics and uncertain physical IDs are
not modeled. They do not establish stellar variability, a calibrated false
alarm rate, or a technosignature. All ten supplement IDs have at least one flag; the source count is recorded
separately from the correlated pair count in the summary. Follow up native spectra, class/epoch consistency and parameter
uncertainty calibration before physical interpretation.

The W1/W2 zero reference is an instrumental color reference, not a validated
white-dwarf photosphere. No clean W3/W4 detections survive this frozen pilot
screen, so this run cannot assess a mid-infrared excess. Five-band technical
readiness does not pass the physical-ID, image, atmosphere-model, matched-control
or false-alarm gates. Zero certified excesses is a status statement, not a
statistically complete survey null result.

## Evidence and reproduction

Archive: https://drive.google.com/drive/folders/1cNcKYI8eylIcyC7iHjnhdVGFayp8UYpF
Machine-readable summary, journal, amended protocol and validation are in reports.
The archive includes failed attempts, all raw responses, source Gaia/CP001 inputs,
per-experiment results, script and hash manifest. Restore the separately archived
SQLite snapshot (SHA256 e27400b570392b21a6a10ebecf5eff4631bb900784c1ba1bda4cd23d7d1b2033).

```
python -m scripts.wd_ten_pilots design_amended.json input_cohort/design.json \
  input_cohort/raw /path/to/verified-staging.sqlite3 /path/to/new-output \
  --replay-raw execution_003/raw
```

Ordinary test CI never retrieves live catalogs. The runner without `--replay-raw`
performs explicitly requested bounded acquisitions; never overwrite an old run.

## Source documentation discrepancy

Native WD FITS metadata labels temperature/error in K and logg/error in dex.
The current online LAMOST Table 14 instead labels logg and logg_err as K:
https://www.lamost.org/dr9/v2.0/doc/lr-data-production-description . This
documentation conflict is retained explicitly. Calculations preserve native
values/units; the discrepancy needs provider review before physical parameter
interpretation. The documented WD uncertainties are least-square fitting
uncertainties, which do not themselves establish a complete predictive/systematic
error model.
