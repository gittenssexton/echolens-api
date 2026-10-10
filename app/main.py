from fastapi import FastAPI

app = FastAPI(title="EchoLens API", version="0.1.0")

@app.get("/")
def root():
    return {"service": "EchoLens API", "status": "online", "docs": "/docs"}

@app.get("/health")
def health():
    return {"status": "ok"}
