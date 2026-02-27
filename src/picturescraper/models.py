from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QueryAnalysis:
    entities: list[str]
    date_range: tuple[int, int] | None
    keywords: list[str]


@dataclass(frozen=True)
class ImageResult:
    image_url: str
    page_url: str
    title_or_alt: str
    source_name: str
    date_if_available: str
    license: str
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class SearchFilters:
    license: str | None = None
    source: str | None = None
    orientation: str | None = None


@dataclass(frozen=True)
class SearchOutput:
    reasoning_steps: str
    results: list[ImageResult] | str
    page: int = 1
    limit: int = 10
    total_results: int = 0
    has_more: bool = False
