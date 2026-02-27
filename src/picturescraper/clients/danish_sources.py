from __future__ import annotations

from urllib.parse import quote_plus, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from picturescraper.models import ImageResult


class DanishSourcesClient:
    """Scrape curated Danish sources for query-relevant article images."""

    SEARCH_URLS = [
        "https://www.skagensavis.dk/?s={q}",
        "https://www.tv2nord.dk/soeg?q={q}",
        "https://nordjyske.dk/soeg?q={q}",
        "https://www.dr.dk/soeg?query={q}",
    ]

    def __init__(self, timeout_seconds: float = 10.0):
        self.timeout_seconds = timeout_seconds
        self.headers = {
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "da,en;q=0.8",
        }

    def search_images(self, query: str, limit: int = 12) -> list[ImageResult]:
        variants = self._query_variants(query)
        all_links: list[str] = []
        for variant in variants:
            all_links.extend(self._collect_article_links(variant, max_links=max(limit * 2, 14)))
        article_links = _dedupe(all_links)[: max(limit * 4, 24)]
        out: list[ImageResult] = []
        for link in article_links:
            article = self._extract_article_image(link)
            if article is None:
                continue
            out.append(article)
            if len(out) >= limit:
                break
        return out

    def _query_variants(self, query: str) -> list[str]:
        tokens = [t for t in query.split() if len(t) >= 3]
        variants = [query]
        low = [t.lower() for t in tokens]
        if "copacabana" in low and "skagen" in low:
            variants.append("copacabana skagen")
        if "copacabana" in low:
            variants.append("copacabana")
        if "skagen" in low and ("diskotek" in low or "discotheque" in low):
            variants.append("skagen diskotek")
        return _dedupe(variants)

    def _collect_article_links(self, query: str, max_links: int) -> list[str]:
        candidates: list[tuple[int, str]] = []
        q = quote_plus(query)
        terms = [t.lower() for t in query.split() if len(t) >= 4]
        for template in self.SEARCH_URLS:
            url = template.format(q=q)
            try:
                response = requests.get(url, headers=self.headers, timeout=self.timeout_seconds)
                if not response.ok:
                    continue
                soup = BeautifulSoup(response.text, "html.parser")
                for a in soup.select("a[href]"):
                    href = a.get("href")
                    if not href:
                        continue
                    abs_url = urljoin(url, href)
                    link_text = " ".join(a.get_text(" ", strip=True).split()).lower()
                    if terms and not any(t in (link_text + " " + abs_url.lower()) for t in terms):
                        continue
                    if not self._is_viable_article_url(abs_url):
                        continue
                    hay = f"{link_text} {abs_url.lower()}"
                    score = sum(1 for t in terms if t in hay)
                    # Prefer specific article-looking URLs with years.
                    if any(f"/{year}/" in abs_url for year in range(2000, 2030)):
                        score += 1
                    candidates.append((score, abs_url))
            except requests.RequestException:
                continue
        candidates.sort(key=lambda pair: pair[0], reverse=True)
        ordered = [url for _, url in candidates]
        return _dedupe(ordered)[:max_links]

    def _extract_article_image(self, page_url: str) -> ImageResult | None:
        try:
            response = requests.get(page_url, headers=self.headers, timeout=self.timeout_seconds)
            if not response.ok:
                return None
            soup = BeautifulSoup(response.text, "html.parser")

            title = ""
            if soup.title and soup.title.get_text(strip=True):
                title = soup.title.get_text(" ", strip=True)

            og = soup.select_one('meta[property="og:image"], meta[name="og:image"]')
            image_url = og.get("content") if og else None
            if not image_url:
                # Fallback to first meaningful img tag.
                for img in soup.select("img[src]"):
                    src = img.get("src")
                    if not src:
                        continue
                    low = src.lower()
                    if any(x in low for x in ["logo", "icon", "avatar", "sprite"]):
                        continue
                    image_url = src
                    break

            if not image_url:
                return None

            lower_img = image_url.lower()
            if any(
                bad in lower_img
                for bad in ["facebooklogo", "pixel", "noscript", "tracking", "doubleclick", "googletagmanager"]
            ):
                return None

            return ImageResult(
                image_url=urljoin(page_url, image_url),
                page_url=page_url,
                title_or_alt=title,
                source_name="dk-web",
                date_if_available="",
                license="unknown",
            )
        except requests.RequestException:
            return None

    def _is_viable_article_url(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return False
        host = parsed.netloc.lower()
        if not host.endswith(".dk") and "dr.dk" not in host:
            return False
        # Skip obvious non-content paths
        bad = [
            "/tag/",
            "/kategori/",
            "/category/",
            "/login",
            "/kontakt",
            "/search",
            "/soeg",
            "/om",
            "/about",
            "/privacy",
            "/wp-content/plugins/",
            "track_click.php",
            "facebook.com/tr?",
        ]
        low = parsed.path.lower()
        full = url.lower()
        if any(b in low for b in bad) or any(b in full for b in bad):
            return False
        if len([part for part in low.split("/") if part]) < 2:
            return False
        return True


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.split("#", 1)[0]
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
    return out
