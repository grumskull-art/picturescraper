from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from picturescraper.clients.flickr import FlickrClient
from picturescraper.clients.openverse import OpenverseClient
from picturescraper.config import settings
from picturescraper.service import PictureSearchService, to_json_dict

app = FastAPI(title="Picture Scraper", version="0.1.0")


def build_service() -> PictureSearchService:
    openverse = OpenverseClient(
        endpoint=settings.openverse_endpoint,
        timeout_seconds=settings.request_timeout_seconds,
    )
    flickr = None
    if settings.flickr_api_key:
        flickr = FlickrClient(
            api_key=settings.flickr_api_key,
            api_secret=settings.flickr_api_secret,
            timeout_seconds=settings.request_timeout_seconds,
        )
    return PictureSearchService(openverse_client=openverse, flickr_client=flickr)


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
