from picturescraper.models import ImageResult
from picturescraper.storage import CollectionStore


def test_store_roundtrip(tmp_path) -> None:
    store = CollectionStore(str(tmp_path / "collections.json"))
    saved = store.create_collection(
        name="test",
        query="mountains",
        filters={"source": "wikimedia"},
        results=[
            ImageResult(
                image_url="https://img.example.com/1.jpg",
                page_url="https://example.com/1",
                title_or_alt="One",
                source_name="wikimedia",
                date_if_available="2020",
                license="by",
                width=100,
                height=50,
            )
        ],
    )

    listed = store.list_collections()
    assert len(listed) == 1
    assert listed[0]["id"] == saved["id"]

    fetched = store.get_collection(saved["id"])
    assert fetched is not None
    assert fetched["name"] == "test"
