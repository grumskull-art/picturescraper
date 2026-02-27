from __future__ import annotations

import requests

from picturescraper.models import ImageResult


class OpenverseClient:
    def __init__(self, endpoint: str, timeout_seconds: float = 10.0):
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds

    def search_images(
        self,
        keyword: str,
        per_keyword_limit: int = 10,
        page: int = 1,
        license_code: str | None = None,
        source: str | None = None,
    ) -> list[ImageResult]:
        params = {
            "q": keyword,
            "page_size": per_keyword_limit,
            "license_type": "all",
            "page": page,
        }
        if license_code:
            params["license"] = license_code
        if source:
            params["source"] = source
        response = requests.get(self.endpoint, params=params, timeout=self.timeout_seconds)
        if not response.ok:
            return []

        payload = response.json()
        results: list[ImageResult] = []
        for item in payload.get("results", []):
            image_url = item.get("url")
            page_url = item.get("foreign_landing_url")
            if not image_url or not page_url:
                continue
            results.append(
                ImageResult(
                    image_url=image_url,
                    page_url=page_url,
                    title_or_alt=item.get("title") or item.get("alt_text") or "",
                    source_name=item.get("source") or "Openverse",
                    date_if_available=item.get("created_on") or "",
                    license=item.get("license") or "",
                    width=item.get("width"),
                    height=item.get("height"),
                )
            )
        return results
