from __future__ import annotations

from dataclasses import asdict
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

from picturescraper.models import ImageResult, QueryAnalysis, SearchOutput
from picturescraper.query import analyze_query


class ImageClient(Protocol):
    def search_images(self, keyword: str, per_keyword_limit: int = 10) -> list[ImageResult]:
        ...


class PictureSearchService:
    def __init__(
        self,
        openverse_client: ImageClient,
        max_year_span: int = 15,
    ):
        self.openverse_client = openverse_client
        self.max_year_span = max_year_span

    def search(self, query: str, limit: int = 10, per_keyword_limit: int = 8) -> SearchOutput:
        analysis = analyze_query(query, max_year_span=self.max_year_span)
        if not analysis.keywords:
            return SearchOutput(
                reasoning_steps="No usable entities found in query.",
                results="[No results found for this query]",
            )

        all_results: list[ImageResult] = []
        used_sources: list[str] = []

        for keyword in analysis.keywords:
            ov_results = self.openverse_client.search_images(keyword, per_keyword_limit=per_keyword_limit)
            if ov_results and "Openverse" not in used_sources:
                used_sources.append("Openverse")
            all_results.extend(ov_results)

        filtered = filter_and_deduplicate(all_results)
        ranked = sort_by_quality(filtered)
        final_results = ranked[:limit]

        reasoning = build_reasoning(analysis, len(used_sources), used_sources)
        if not final_results:
            return SearchOutput(reasoning_steps=reasoning, results="[No results found for this query]")
        return SearchOutput(reasoning_steps=reasoning, results=final_results)


def filter_and_deduplicate(image_results: list[ImageResult]) -> list[ImageResult]:
    seen = set()
    filtered: list[ImageResult] = []
    for res in image_results:
        normalized = normalize_url(res.image_url)
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        filtered.append(res)
    return filtered


def sort_by_quality(results: list[ImageResult]) -> list[ImageResult]:
    return sorted(results, key=_quality_score, reverse=True)


def _quality_score(result: ImageResult) -> int:
    dimensions = (result.width or 0) * (result.height or 0)
    has_title = 1 if result.title_or_alt.strip() else 0
    has_date = 1 if result.date_if_available.strip() else 0
    return dimensions + has_title * 5000 + has_date * 3000


def normalize_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), parts.path, "", ""))
    except ValueError:
        return ""


def build_reasoning(analysis: QueryAnalysis, n_sources: int, source_names: list[str]) -> str:
    date_text = (
        f"{analysis.date_range[0]}-{analysis.date_range[1]}"
        if analysis.date_range is not None
        else "none"
    )
    keyword_examples = ", ".join(analysis.keywords[:2])
    source_text = ", ".join(source_names) if source_names else "none"
    return (
        "Analyzed query for entities and optional dates. "
        f"Entities: {analysis.entities}. Date range: {date_text}. "
        f"Generated keyword variations such as {keyword_examples}. "
        f"Searched {n_sources} source(s): {source_text}. "
        "Deduplicated by URL and ranked by basic quality signals."
    )


def to_json_dict(output: SearchOutput) -> dict:
    if isinstance(output.results, str):
        results = output.results
    else:
        results = [asdict(item) for item in output.results]
    return {
        "reasoning_steps": output.reasoning_steps,
        "results": results,
    }
