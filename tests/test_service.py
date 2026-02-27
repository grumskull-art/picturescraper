from picturescraper.models import ImageResult, SearchFilters
from picturescraper.service import PictureSearchService


class FakeOpenverse:
    def search_images(
        self,
        keyword: str,
        per_keyword_limit: int = 10,
        page: int = 1,
        license_code: str | None = None,
        source: str | None = None,
    ):
        if page > 1:
            return [
                ImageResult(
                    image_url="https://img.example.com/c.jpg",
                    page_url="https://example.com/c",
                    title_or_alt="C",
                    source_name="wikimedia",
                    date_if_available="2002",
                    license="by",
                    width=1600,
                    height=900,
                )
            ]

        return [
            ImageResult(
                image_url="https://img.example.com/a.jpg?foo=1",
                page_url="https://example.com/a",
                title_or_alt="A",
                source_name="flickr",
                date_if_available="1999",
                license="by",
                width=640,
                height=480,
            ),
            ImageResult(
                image_url="https://img.example.com/a.jpg?foo=2",
                page_url="https://example.com/a-dup",
                title_or_alt="",
                source_name="flickr",
                date_if_available="",
                license="by",
                width=0,
                height=0,
            ),
            ImageResult(
                image_url="https://img.example.com/b.jpg",
                page_url="https://example.com/b",
                title_or_alt="B",
                source_name="wikimedia",
                date_if_available="2001",
                license="by-sa",
                width=1200,
                height=900,
            ),
        ]


def test_service_deduplicates_and_ranks() -> None:
    service = PictureSearchService(openverse_client=FakeOpenverse())
    out = service.search("Copacabana 1999", limit=10)

    assert isinstance(out.results, list)
    assert len(out.results) == 2
    assert out.results[0].image_url == "https://img.example.com/b.jpg"
    assert "Deduplicated by URL" in out.reasoning_steps


def test_service_applies_filters_and_pagination() -> None:
    service = PictureSearchService(openverse_client=FakeOpenverse())
    out = service.search(
        "Copacabana 1999",
        limit=1,
        page=2,
        filters=SearchFilters(source="wikimedia", orientation="landscape"),
    )

    assert isinstance(out.results, list)
    assert len(out.results) == 1
    assert out.results[0].image_url == "https://img.example.com/b.jpg"
    assert out.total_results == 2


class FakeOpenverseEntityFallback:
    def search_images(
        self,
        keyword: str,
        per_keyword_limit: int = 10,
        page: int = 1,
        license_code: str | None = None,
        source: str | None = None,
    ):
        k = keyword.lower()
        if "copa cabana skagen" in k:
            return []
        if "copacabana" in k:
            return [
                ImageResult(
                    image_url="https://img.example.com/copacabana.jpg",
                    page_url="https://example.com/copacabana",
                    title_or_alt="Copacabana beach",
                    source_name="wikimedia",
                    date_if_available="2001",
                    license="by-sa",
                    width=2000,
                    height=1200,
                )
            ]
        if "skagen" in k:
            return [
                ImageResult(
                    image_url="https://img.example.com/skagen.jpg",
                    page_url="https://example.com/skagen",
                    title_or_alt="Skagen coast",
                    source_name="wikimedia",
                    date_if_available="2003",
                    license="by",
                    width=1800,
                    height=1200,
                )
            ]
        return []


def test_service_entity_fallback_returns_real_terms() -> None:
    service = PictureSearchService(openverse_client=FakeOpenverseEntityFallback())
    out = service.search("Copa cabana skagen 1994-2010", limit=10)

    assert isinstance(out.results, list)
    urls = [r.image_url for r in out.results]
    assert "https://img.example.com/copacabana.jpg" in urls
    assert "https://img.example.com/skagen.jpg" in urls


class FakeOpenverseEmpty:
    def search_images(
        self,
        keyword: str,
        per_keyword_limit: int = 10,
        page: int = 1,
        license_code: str | None = None,
        source: str | None = None,
    ):
        return []


class FakeWebFallback:
    def search_images(self, query: str, limit: int = 8):
        return [
            ImageResult(
                image_url="https://img.example.com/web.jpg",
                page_url="https://example.com/event",
                title_or_alt="Diskotek Copacabana i Skagen",
                source_name="web",
                date_if_available="",
                license="unknown",
                width=1200,
                height=800,
            )
        ]


def test_service_uses_web_fallback_when_openverse_empty() -> None:
    class FakeBingEmpty:
        def search_images(self, query: str, limit: int = 8):
            return []

    service = PictureSearchService(
        openverse_client=FakeOpenverseEmpty(),
        bing_images_client=FakeBingEmpty(),
        web_fallback_client=FakeWebFallback(),
    )
    out = service.search("mountain sunset", limit=10)

    assert isinstance(out.results, list)
    assert out.results[0].source_name == "web"


def test_service_prefers_bing_images_for_nightlife_queries() -> None:
    class FakeBing:
        def search_images(self, query: str, limit: int = 8):
            return [
                ImageResult(
                    image_url="https://img.example.com/bing.jpg",
                    page_url="https://example.com/copacabana-skagen-night",
                    title_or_alt="Diskotek Copacabana Skagen",
                    source_name="bing-images",
                    date_if_available="",
                    license="unknown",
                    width=1600,
                    height=900,
                )
            ]

    service = PictureSearchService(
        openverse_client=FakeOpenverseEmpty(),
        bing_images_client=FakeBing(),
        web_fallback_client=FakeWebFallback(),
    )
    out = service.search("diskotek Copacabana Skagen", limit=10)

    assert isinstance(out.results, list)
    assert out.results[0].source_name == "bing-images"
