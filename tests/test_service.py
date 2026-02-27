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


class FakeDanishWeb:
    def search_images(self, query: str, limit: int = 12):
        return [
            ImageResult(
                image_url="https://img.example.com/dk.jpg",
                page_url="https://www.skagensavis.dk/copacabana-skagen",
                title_or_alt="Copacabana i Skagen",
                source_name="dk-web",
                date_if_available="",
                license="unknown",
                width=1000,
                height=700,
            )
        ]


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


def test_service_uses_danish_web_fallback() -> None:
    service = PictureSearchService(
        openverse_client=FakeOpenverseEmpty(),
        danish_web_client=FakeDanishWeb(),
    )
    out = service.search("diskotek Copacabana Skagen", limit=10)

    assert isinstance(out.results, list)
    assert out.results[0].source_name == "dk-web"
