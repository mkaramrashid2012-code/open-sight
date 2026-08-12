from fastapi import FastAPI
from app.api.cameras import router as cameras_router
from app.api.search import router as search_router

app = FastAPI(title="OpenSight Private API", version="0.1.0")
app.include_router(cameras_router, prefix="/api/v1")
app.include_router(search_router, prefix="/api/v1")

@app.get("/api/v1/health")
def health():
    return {"status": "ok", "service": "opensight-api"}
