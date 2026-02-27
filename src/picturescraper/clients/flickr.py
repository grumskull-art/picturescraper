from __future__ import annotations

import requests

from picturescraper.models import ImageResult

FLICKR_API_ENDPOINT = "https://api.flickr.com/services/rest/"

LICENSE_MAP = {
    "0": "All Rights Reserved",
    "1": "CC BY-NC-SA 2.0",
    "2": "CC BY-NC 2.0",
    "3": "CC BY-NC-ND 2.0",
    "4": "CC BY 2.0",
    "5": "CC BY-SA 2.0",
    "6": "CC BY-ND 2.0",
    "7": "No known copyright restrictions",
    "8": "US Government Work",
    "9": "CC0 1.0",
    "10": "Public Domain Mark",
}


class FlickrClient:
    def __init__(
        self,
        api_key: str,
        api_secret: str | None = None,
        timeout_seconds: float = 10.0,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.timeout_seconds = timeout_seconds

    def search_images(
        self,
        keyword: str,
        per_keyword_limit: int = 10,
        date_range: tuple[int, int] | None = None,
    ) -> list[ImageResult]:
        params: dict[str, str | int] = {
            "method": "flickr.photos.search",
            "api_key": self.api_key,
            "text": keyword,
            "per_page": per_keyword_limit,
            "page": 1,
            "media": "photos",
            "sort": "relevance",
            "content_type": 1,
            "safe_search": 1,
            "extras": "owner_name,date_taken,license,url_c,url_l,url_o,o_dims",
            "format": "json",
            "nojsoncallback": 1,
        }
        if date_range is not None:
            start, end = date_range
            params["min_taken_date"] = f"{start}-01-01"
            params["max_taken_date"] = f"{end}-12-31"

        response = requests.get(FLICKR_API_ENDPOINT, params=params, timeout=self.timeout_seconds)
        if not response.ok:
            return []

        payload = response.json()
        photos = payload.get("photos", {}).get("photo", [])
        results: list[ImageResult] = []
        for photo in photos:
            image_url = photo.get("url_o") or photo.get("url_l") or photo.get("url_c")
            owner = photo.get("owner")
            photo_id = photo.get("id")
            if not image_url or not owner or not photo_id:
                continue
            results.append(
                ImageResult(
                    image_url=image_url,
                    page_url=f"https://www.flickr.com/photos/{owner}/{photo_id}",
                    title_or_alt=photo.get("title") or "",
                    source_name="Flickr",
                    date_if_available=photo.get("datetaken") or "",
                    license=LICENSE_MAP.get(str(photo.get("license", "")), "Unknown"),
                    width=_to_int(photo.get("width_o") or photo.get("width_l") or photo.get("width_c")),
                    height=_to_int(
                        photo.get("height_o") or photo.get("height_l") or photo.get("height_c")
                    ),
                )
            )
        return results


def _to_int(value: object) -> int | None:
    if value is None:
        return None
    try:
        return int(str(value))
    except ValueError:
        return None
