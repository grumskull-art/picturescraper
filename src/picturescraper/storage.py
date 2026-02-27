from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from picturescraper.models import ImageResult


class CollectionStore:
    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self._write([])

    def list_collections(self) -> list[dict]:
        return self._read()

    def get_collection(self, collection_id: str) -> dict | None:
        for item in self._read():
            if item["id"] == collection_id:
                return item
        return None

    def create_collection(
        self,
        name: str,
        query: str,
        filters: dict,
        results: list[ImageResult],
    ) -> dict:
        record = {
            "id": str(uuid4()),
            "name": name.strip(),
            "query": query,
            "filters": filters,
            "created_at": datetime.now(UTC).isoformat(),
            "result_count": len(results),
            "results": [asdict(r) for r in results],
        }
        data = self._read()
        data.insert(0, record)
        self._write(data)
        return record

    def _read(self) -> list[dict]:
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write(self, data: list[dict]) -> None:
        self.path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
