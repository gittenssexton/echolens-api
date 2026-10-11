from fastapi import FastAPI, HTTPException, Query

from app.catalog import get_star, list_stars, stats

app = FastAPI(title="EchoLens API", version="0.2.0")

@app.get("/")
def root():
    return {"service": "EchoLens API", "status": "online", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/stars")
def search_stars(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    max_g_mag: float | None = None,
    min_parallax: float | None = None,
):
    return list_stars(limit=limit, offset=offset, max_g_mag=max_g_mag, min_parallax=min_parallax)

@app.get("/stars/stats")
def star_stats():
    return stats()

@app.get("/stars/{source_id}")
def inspect_star(source_id: str):
    if not source_id.isdigit():
        raise HTTPException(status_code=400, detail="Gaia source_id must be numeric")
    record = get_star(source_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Star not present in the imported registry")
    return {"star": record, "measurement_source": "Gaia DR3", "ai_interpretation": None}
