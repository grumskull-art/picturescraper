from __future__ import annotations

from dataclasses import asdict
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit

from picturescraper.models import ImageResult, QueryAnalysis, SearchFilters, SearchOutput
from picturescraper.query import analyze_query


class ImageClient(Protocol):
    def search_images(
        self,
        keyword: str,
        per_keyword_limit: int = 10,
        page: int = 1,
        license_code: str | None = None,
        source: str | None = None,
    ) -> list[ImageResult]:
        ...


class PictureSearchService:
    def __init__(
        self,
        openverse_client: ImageClient,
        max_year_span: int = 15,
    ):
        self.openverse_client = openverse_client
        self.max_year_span = max_year_span

    def search(
        self,
        query: str,
        limit: int = 10,
        page: int = 1,
        per_keyword_limit: int = 20,
        filters: SearchFilters | None = None,
    ) -> SearchOutput:
        analysis = analyze_query(query, max_year_span=self.max_year_span)
        active_filters = filters or SearchFilters()

        if not analysis.keywords:
            return SearchOutput(
                reasoning_steps="No usable entities found in query.",
                results="[No results found for this query]",
                page=page,
                limit=limit,
                total_results=0,
                has_more=False,
            )

        all_results: list[ImageResult] = []
        used_sources: list[str] = []

        for keyword in analysis.keywords:
            for openverse_page in range(1, page + 1):
                ov_results = self.openverse_client.search_images(
                    keyword,
                    per_keyword_limit=per_keyword_limit,
                    page=openverse_page,
                    license_code=active_filters.license,
                    source=active_filters.source,
                )
                if ov_results and "Openverse" not in used_sources:
                    used_sources.append("Openverse")
                all_results.extend(ov_results)

        deduped = filter_and_deduplicate(all_results)
        constrained = apply_filters(deduped, active_filters)
        ranked = sort_by_quality(constrained)

        total_results = len(ranked)
        start = (page - 1) * limit
        end = start + limit
        final_results = ranked[start:end]

        reasoning = build_reasoning(analysis, len(used_sources), used_sources, active_filters)
        if not final_results:
            return SearchOutput(
                reasoning_steps=reasoning,
                results="[No results found for this query]",
                page=page,
                limit=limit,
                total_results=total_results,
                has_more=False,
            )

        has_more = end < total_results
        return SearchOutput(
            reasoning_steps=reasoning,
            results=final_results,
            page=page,
            limit=limit,
            total_results=total_results,
            has_more=has_more,
        )


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


def apply_filters(results: list[ImageResult], filters: SearchFilters) -> list[ImageResult]:
    out = results

    if filters.license:
        match = filters.license.lower()
        out = [r for r in out if match in r.license.lower()]

    if filters.source:
        match = filters.source.lower()
        out = [r for r in out if match in r.source_name.lower()]

    if filters.orientation:
        out = [r for r in out if _orientation_of(r) == filters.orientation]

    return out


def _orientation_of(result: ImageResult) -> str | None:
    if result.width is None or result.height is None or result.width == 0 or result.height == 0:
        return None
    if result.width > result.height:
        return "landscape"
    if result.width < result.height:
        return "portrait"
    return "square"


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


def build_reasoning(
    analysis: QueryAnalysis,
    n_sources: int,
    source_names: list[str],
    filters: SearchFilters,
) -> str:
    date_text = (
        f"{analysis.date_range[0]}-{analysis.date_range[1]}"
        if analysis.date_range is not None
        else "none"
    )
    keyword_examples = ", ".join(analysis.keywords[:2])
    source_text = ", ".join(source_names) if source_names else "none"
    filters_text = ", ".join(
        [
            f"license={filters.license}" if filters.license else "",
            f"source={filters.source}" if filters.source else "",
            f"orientation={filters.orientation}" if filters.orientation else "",
        ]
    )
    filters_text = ", ".join([p for p in filters_text.split(", ") if p]) or "none"

    return (
        "Analyzed query for entities and optional dates. "
        f"Entities: {analysis.entities}. Date range: {date_text}. "
        f"Generated keyword variations such as {keyword_examples}. "
        f"Searched {n_sources} source(s): {source_text}. "
        f"Applied filters: {filters_text}. "
        "Deduplicated by URL and ranked by basic quality signals."
    )


def to_json_dict(output: SearchOutput) -> dict:
    if isinstance(output.results, str):
        results = output.results
        count = 0
        next_page = None
    else:
        results = [asdict(item) for item in output.results]
        count = len(results)
        next_page = output.page + 1 if output.has_more else None

    return {
        "reasoning_steps": output.reasoning_steps,
        "results": results,
        "page": output.page,
        "limit": output.limit,
        "count": count,
        "total_results": output.total_results,
        "has_more": output.has_more,
        "next_page": next_page,
    }
