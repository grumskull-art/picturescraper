from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from picturescraper.clients.openverse import OpenverseClient
from picturescraper.config import settings
from picturescraper.service import PictureSearchService, to_json_dict

app = FastAPI(title="Picture Scraper", version="0.1.0")
WEB_DIR = Path(__file__).resolve().parent / "web"
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


def build_service() -> PictureSearchService:
    openverse = OpenverseClient(
        endpoint=settings.openverse_endpoint,
        timeout_seconds=settings.request_timeout_seconds,
    )
    return PictureSearchService(openverse_client=openverse)


@app.get("/")
def web_app() -> FileResponse:
    return FileResponse(WEB_DIR / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/search")
def search_images(
    q: str = Query(..., min_length=2, description="Image search query"),
    limit: int = Query(10, ge=1, le=50),
) -> dict:
    service = build_service()
    try:
        output = service.search(q, limit=limit)
        return to_json_dict(output)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc
