from picturescraper.models import ImageResult
from picturescraper.service import PictureSearchService


class FakeOpenverse:
    def search_images(self, keyword: str, per_keyword_limit: int = 10):
        return [
            ImageResult(
                image_url="https://img.example.com/a.jpg?foo=1",
                page_url="https://example.com/a",
                title_or_alt="A",
                source_name="Openverse",
                date_if_available="1999",
                license="CC BY",
                width=640,
                height=480,
            )
        ]


class FakeFlickr:
    def search_images(self, keyword: str, per_keyword_limit: int = 10, date_range=None):
        return [
            ImageResult(
                image_url="https://img.example.com/a.jpg?foo=2",
                page_url="https://flickr.com/photos/x/1",
                title_or_alt="",
                source_name="Flickr",
                date_if_available="",
                license="CC BY",
                width=0,
                height=0,
            ),
            ImageResult(
                image_url="https://img.example.com/b.jpg",
                page_url="https://flickr.com/photos/x/2",
                title_or_alt="B",
                source_name="Flickr",
                date_if_available="2001",
                license="CC BY-SA",
                width=1200,
                height=900,
            ),
        ]


def test_service_deduplicates_and_ranks() -> None:
    service = PictureSearchService(openverse_client=FakeOpenverse(), flickr_client=FakeFlickr())
    out = service.search("Copacabana 1999", limit=10)

    assert isinstance(out.results, list)
    assert len(out.results) == 2
    assert out.results[0].image_url == "https://img.example.com/b.jpg"
    assert "Deduplicated by URL" in out.reasoning_steps
