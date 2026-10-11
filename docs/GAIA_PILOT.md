# EchoLens Gaia DR3 pilot — reproducibility notes

**Status:** Code and workflow prepared; **no Gaia observations are included in this commit**.
The pilot produces **10,000 real Gaia DR3 source records** only after the fetch and validation job succeeds.

## Selection (version 0.1)

The importer queries the official ESA Gaia DR3 TAP archive at
`https://gea.esac.esa.int/tap-server/tap/sync` and stores the exact ADQL
and SHA-256 digests with the ingest run. Fixed `random_index` range and
`ORDER BY random_index` make selection repeatable for a fixed Gaia DR3 release.
The quality cuts (parallax SNR >= 5, RUWE < 1.4, G and BP-RP available)
mean **this is NOT a representative sample of all Gaia sources**.
A quality-selected pilot is useful for testing ingestion, not for unbiased
technosignature prevalence estimates. We do not assume these stars lack life.

## Run

From the repository root:

```sh
python -m unittest discover -s tests -v
python -m scripts.import_gaia --fetch --db data/echolens.sqlite
```

Alternatively import a previously retrieved Gaia CSV with
`python -m scripts.import_gaia --csv path/to/gaia.csv --db data/echolens.sqlite`.

The manual GitHub Actions workflow **Gaia DR3 10k pilot import** runs the
same command and publishes a temporary downloadable artifact containing:
`data/echolens.sqlite`, the exact raw CSV and a JSON manifest.
Transfer validated artifacts to the EchoLens Drive archive for durable retention;
GitHub Actions artifact retention is not permanent storage.

## API

Set `ECHOLENS_DB_PATH` to an existing SQLite database file. Routes:
- `GET /health` — current health check
- `GET /stars/stats` — record count and database-loaded status
- `GET /stars?limit=50&offset=0&max_g_mag=14&min_parallax=1`
- `GET /stars/{source_id}` — measured values and provenance

No database file means zero results with `database_loaded=false` —
**never simulated data**. Render's normal service filesystem is not durable;
use persistent storage or a managed database before enabling production records.

## Scientific limitations and follow-up

Gaia DR3 `gaia_source` is a source catalog, not proof that every entry is
an isolated physical star. Validate source classifications, binaries, and
catalog flags before constructing reference controls. Negative or uncertain
parallaxes must not be converted naively to distances. Gaia DR3 measured
quantities are stored separately from any future inferred distances, luminosities,
WISE matches or AI interpretations. The initial API exposes measured columns only.

Reference: https://www.cosmos.esa.int/web/gaia/dr3
