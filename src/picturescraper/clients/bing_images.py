from __future__ import annotations

import json

import requests
from bs4 import BeautifulSoup

from picturescraper.models import ImageResult


class BingImagesClient:
    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.8,da;q=0.7",
        }

    def search_images(self, query: str, limit: int = 12) -> list[ImageResult]:
        try:
            response = requests.get(
                "https://www.bing.com/images/search",
                params={"q": query, "form": "HDRSC2"},
                headers=self.headers,
                timeout=self.timeout_seconds,
            )
            if not response.ok:
                return []

            soup = BeautifulSoup(response.text, "html.parser")
            out: list[ImageResult] = []
            for a in soup.select("a.iusc"):
                blob = a.get("m")
                if not blob:
                    continue
                try:
                    data = json.loads(blob)
                except json.JSONDecodeError:
                    continue

                image_url = data.get("murl")
                page_url = data.get("purl")
                title = data.get("t") or ""
                if not image_url or not page_url:
                    continue

                out.append(
                    ImageResult(
                        image_url=image_url,
                        page_url=page_url,
                        title_or_alt=title,
                        source_name="bing-images",
                        date_if_available="",
                        license="unknown",
                    )
                )
                if len(out) >= limit:
                    break
            return out
        except requests.RequestException:
            return []
