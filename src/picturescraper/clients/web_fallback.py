from __future__ import annotations

import base64
from urllib.parse import parse_qs, unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from picturescraper.models import ImageResult


class WebFallbackClient:
    """Query web pages and extract representative images (og:image or first content image)."""

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "en-US,en;q=0.8,da;q=0.7",
        }

    def search_images(self, query: str, limit: int = 8) -> list[ImageResult]:
        links = self._bing_links(query, limit=limit * 2)
        if not links:
            links = self._duckduckgo_links(query, limit=limit * 2)
        out: list[ImageResult] = []
        for page_url, title in links:
            image_url = self._extract_image_from_page(page_url)
            if not image_url:
                continue
            out.append(
                ImageResult(
                    image_url=image_url,
                    page_url=page_url,
                    title_or_alt=title or "",
                    source_name="web",
                    date_if_available="",
                    license="unknown",
                )
            )
            if len(out) >= limit:
                break
        return out

    def _bing_links(self, query: str, limit: int) -> list[tuple[str, str]]:
        try:
            response = requests.get(
                "https://www.bing.com/search",
                params={"q": query},
                headers=self.headers,
                timeout=self.timeout_seconds,
            )
            if not response.ok:
                return []
            soup = BeautifulSoup(response.text, "html.parser")
            links: list[tuple[str, str]] = []
            for a in soup.select("li.b_algo h2 a"):
                href = a.get("href")
                if not href:
                    continue
                href = _normalize_bing_href(href)
                if not href or not href.startswith("http"):
                    continue
                title = " ".join(a.get_text(" ", strip=True).split())
                links.append((href, title))
                if len(links) >= limit:
                    break
            return links
        except requests.RequestException:
            return []

    def _duckduckgo_links(self, query: str, limit: int) -> list[tuple[str, str]]:
        try:
            response = requests.get(
                "https://duckduckgo.com/html/",
                params={"q": query},
                headers=self.headers,
                timeout=self.timeout_seconds,
            )
            if not response.ok:
                return []
            soup = BeautifulSoup(response.text, "html.parser")
            links: list[tuple[str, str]] = []
            for a in soup.select("a.result__a"):
                href = a.get("href")
                if not href:
                    continue
                href = _normalize_ddg_href(href)
                if not href or not href.startswith("http"):
                    continue
                title = " ".join(a.get_text(" ", strip=True).split())
                links.append((href, title))
                if len(links) >= limit:
                    break
            return links
        except requests.RequestException:
            return []

    def _extract_image_from_page(self, page_url: str) -> str | None:
        try:
            response = requests.get(
                page_url,
                headers=self.headers,
                timeout=self.timeout_seconds,
                allow_redirects=True,
            )
            if not response.ok:
                return None
            soup = BeautifulSoup(response.text, "html.parser")

            og = soup.select_one('meta[property="og:image"], meta[name="og:image"]')
            if og and og.get("content"):
                return urljoin(page_url, og["content"])

            for img in soup.select("img[src]"):
                src = img.get("src")
                if not src:
                    continue
                lower = src.lower()
                if any(x in lower for x in ["logo", "icon", "sprite", "avatar"]):
                    continue
                return urljoin(page_url, src)
        except requests.RequestException:
            return None
        return None


def _normalize_ddg_href(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/l/?") or href.startswith("//duckduckgo.com/l/?"):
        parsed = urlparse(href if href.startswith("http") else f"https://duckduckgo.com{href}")
        uddg = parse_qs(parsed.query).get("uddg")
        if uddg:
            return unquote(uddg[0])
    return href


def _normalize_bing_href(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        parsed = urlparse(href)
        if "bing.com" not in parsed.netloc or not parsed.path.startswith("/ck/"):
            return href
        encoded = parse_qs(parsed.query).get("u", [""])[0]
        if encoded.startswith("a1"):
            try:
                payload = encoded[2:]
                padding = "=" * (-len(payload) % 4)
                decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8", errors="ignore")
                if decoded.startswith("http://") or decoded.startswith("https://"):
                    return decoded
            except Exception:
                return href
    return href
