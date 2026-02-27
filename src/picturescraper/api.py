from __future__ import annotations

from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from picturescraper.clients.openverse import OpenverseClient
from picturescraper.config import settings
from picturescraper.models import SearchFilters
from picturescraper.service import PictureSearchService, to_json_dict
from picturescraper.storage import CollectionStore

app = FastAPI(title="Picture Scraper", version="0.2.0")
WEB_DIR = Path(__file__).resolve().parent / "web"
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
store = CollectionStore(settings.collections_path)


class SaveCollectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    query: str = Field(min_length=2, max_length=500)
    filters: dict = Field(default_factory=dict)
    results: list[dict] = Field(default_factory=list)


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
    limit: int = Query(12, ge=1, le=50),
    page: int = Query(1, ge=1),
    license: str | None = Query(None, max_length=80),
    source: str | None = Query(None, max_length=80),
    orientation: Literal["landscape", "portrait", "square"] | None = Query(None),
) -> dict:
    service = build_service()
    try:
        filters = SearchFilters(
            license=license.strip() if license else None,
            source=source.strip() if source else None,
            orientation=orientation,
        )
        output = service.search(q, limit=limit, page=page, filters=filters)
        return to_json_dict(output)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Search failed: {exc}") from exc


@app.get("/collections")
def list_collections() -> dict:
    return {"collections": store.list_collections()}


@app.get("/collections/{collection_id}")
def get_collection(collection_id: str) -> dict:
    collection = store.get_collection(collection_id)
    if collection is None:
        raise HTTPException(status_code=404, detail="Collection not found")
    return collection


@app.post("/collections")
def create_collection(payload: SaveCollectionRequest) -> dict:
    try:
        image_results = []
        for item in payload.results:
            image_results.append(
                {
                    "image_url": item.get("image_url", ""),
                    "page_url": item.get("page_url", ""),
                    "title_or_alt": item.get("title_or_alt", ""),
                    "source_name": item.get("source_name", ""),
                    "date_if_available": item.get("date_if_available", ""),
                    "license": item.get("license", ""),
                    "width": item.get("width"),
                    "height": item.get("height"),
                }
            )
        # Reuse storage schema directly with a dict list for frontend compatibility.
        collection = store.create_collection(
            name=payload.name,
            query=payload.query,
            filters=payload.filters,
            results=[_dict_to_result(item) for item in image_results],
        )
        return collection
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to save collection: {exc}") from exc


def _dict_to_result(item: dict):
    from picturescraper.models import ImageResult

    return ImageResult(
        image_url=item["image_url"],
        page_url=item["page_url"],
        title_or_alt=item["title_or_alt"],
        source_name=item["source_name"],
        date_if_available=item["date_if_available"],
        license=item["license"],
        width=item.get("width"),
        height=item.get("height"),
    )
