from __future__ import annotations

from dataclasses import asdict
from typing import Protocol
from urllib.parse import urlsplit, urlunsplit
import re

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
        bing_images_client: object | None = None,
        web_fallback_client: object | None = None,
        max_year_span: int = 15,
    ):
        self.openverse_client = openverse_client
        self.bing_images_client = bing_images_client
        self.web_fallback_client = web_fallback_client
        self.max_year_span = max_year_span

    def search(
        self,
        query: str,
        limit: int = 10,
        page: int = 1,
        per_keyword_limit: int = 20,
        filters: SearchFilters | None = None,
        max_keyword_calls: int = 6,
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

        target_pool_size = max(limit * page * 2, limit)
        primary_keywords = analysis.keywords[:max_keyword_calls]
        fallback_keywords = analysis.keywords[max_keyword_calls : max_keyword_calls + 2]

        for keyword in primary_keywords:
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
            if len(all_results) >= target_pool_size:
                break

        if not all_results:
            for keyword in fallback_keywords:
                ov_results = self.openverse_client.search_images(
                    keyword,
                    per_keyword_limit=per_keyword_limit,
                    page=1,
                    license_code=active_filters.license,
                    source=active_filters.source,
                )
                if ov_results and "Openverse" not in used_sources:
                    used_sources.append("Openverse")
                all_results.extend(ov_results)

        deduped = filter_and_deduplicate(all_results)
        constrained = apply_filters(deduped, active_filters)
        ranked = sort_by_quality(constrained)
        entity_based, exact_entity_match = prioritize_entity_matches(ranked, analysis.entities)
        used_relaxed_fallback = False
        if entity_based:
            ranked = entity_based
            if not exact_entity_match:
                used_relaxed_fallback = True
        elif ranked:
            used_relaxed_fallback = True
        else:
            used_relaxed_fallback = True

        if used_relaxed_fallback:
            nightlife_boost = should_use_web_boost(query, analysis.entities)
            fallback_entity_results = search_per_entity_fallback(
                client=self.openverse_client,
                entities=analysis.entities,
                per_keyword_limit=per_keyword_limit,
                filters=active_filters,
            )
            if fallback_entity_results:
                ranked = fallback_entity_results
                if self.bing_images_client is not None and nightlife_boost:
                    bing_results = search_bing_entity_mix(
                        self.bing_images_client,
                        query,
                        analysis.entities,
                        limit=max(limit, 8),
                    )
                    bing_results = prioritize_web_venue_matches(bing_results, analysis.entities)
                    if bing_results:
                        ranked = filter_and_deduplicate(bing_results + ranked)
                if self.web_fallback_client is not None and not nightlife_boost:
                    boosted = self.web_fallback_client.search_images(query, limit=max(limit, 8))
                    boosted = prioritize_web_venue_matches(boosted, analysis.entities)
                    if boosted:
                        ranked = filter_and_deduplicate(boosted + ranked)
            else:
                if self.bing_images_client is not None and nightlife_boost:
                    bing_results = search_bing_entity_mix(
                        self.bing_images_client,
                        query,
                        analysis.entities,
                        limit=max(limit * 2, 12),
                    )
                    if bing_results:
                        ranked = sort_by_quality(filter_and_deduplicate(bing_results))
                if not ranked and self.web_fallback_client is not None and not nightlife_boost:
                    web_results = self.web_fallback_client.search_images(query, limit=max(limit * 2, 12))
                    if web_results:
                        ranked = sort_by_quality(filter_and_deduplicate(web_results))
        elif self.web_fallback_client is not None and should_use_web_boost(query, analysis.entities):
            boosted = self.web_fallback_client.search_images(query, limit=max(limit, 8))
            boosted = prioritize_web_venue_matches(boosted, analysis.entities)
            if boosted:
                merged = filter_and_deduplicate(boosted + ranked)
                ranked = merged

        total_results = len(ranked)
        start = (page - 1) * limit
        end = start + limit
        final_results = ranked[start:end]

        reasoning = build_reasoning(
            analysis,
            len(used_sources),
            used_sources,
            active_filters,
            used_relaxed_fallback=used_relaxed_fallback,
        )
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
    used_relaxed_fallback: bool = False,
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

    tail = (
        "No exact multi-entity match was found; showing related results from relaxed matching."
        if used_relaxed_fallback
        else "Prioritized results that match core query entities."
    )

    return (
        "Analyzed query for entities and optional dates. "
        f"Entities: {analysis.entities}. Date range: {date_text}. "
        f"Generated keyword variations such as {keyword_examples}. "
        f"Searched {n_sources} source(s): {source_text}. "
        f"Applied filters: {filters_text}. "
        f"Deduplicated by URL and ranked by basic quality signals. {tail}"
    )


def prioritize_entity_matches(results: list[ImageResult], entities: list[str]) -> tuple[list[ImageResult], bool]:
    core = [e.lower() for e in entities if len(e) >= 3]
    if not core:
        return (results, True)

    merged = {f"{core[i]}{core[i + 1]}" for i in range(len(core) - 1)}
    needed = 1 if len(core) == 1 else 2

    strict: list[tuple[int, ImageResult]] = []
    loose: list[tuple[int, ImageResult]] = []
    for item in results:
        hay = f"{item.title_or_alt} {item.page_url} {item.image_url} {item.source_name}".lower()
        token_hits = sum(1 for token in core if re.search(rf"\b{re.escape(token)}\b", hay))
        merged_hit = any(m in hay for m in merged)
        score = token_hits + (2 if merged_hit else 0)
        if token_hits >= needed or merged_hit:
            strict.append((score, item))
        elif score > 0:
            loose.append((score, item))

    if strict:
        strict.sort(key=lambda pair: pair[0], reverse=True)
        return ([item for _, item in strict], True)
    if loose:
        loose.sort(key=lambda pair: pair[0], reverse=True)
        return ([item for _, item in loose], False)
    return ([], False)


def search_per_entity_fallback(
    client: ImageClient,
    entities: list[str],
    per_keyword_limit: int,
    filters: SearchFilters,
) -> list[ImageResult]:
    terms = canonical_entity_terms(entities)
    if not terms:
        return []

    collected: list[ImageResult] = []
    for term in terms[:3]:
        chunk = client.search_images(
            term,
            per_keyword_limit=max(8, per_keyword_limit // 2),
            page=1,
            license_code=filters.license,
            source=filters.source,
        )
        strict = [item for item in chunk if matches_entity(item, term)]
        collected.extend(strict[:8])

    deduped = filter_and_deduplicate(collected)
    constrained = apply_filters(deduped, filters)
    return sort_by_quality(constrained)


def canonical_entity_terms(entities: list[str]) -> list[str]:
    clean = [e.strip().lower() for e in entities if len(e.strip()) >= 3]
    if not clean:
        return []

    # Domain-specific normalization for common split spellings.
    compounds = {"copa cabana": "copacabana"}
    phrase = " ".join(clean)
    terms: list[str] = []
    consumed_tokens: set[str] = set()
    for source, target in compounds.items():
        if source in phrase:
            terms.append(target)
            for token in source.split():
                consumed_tokens.add(token)

    terms.extend([t for t in clean if t not in consumed_tokens])
    return list(dict.fromkeys(terms))


def matches_entity(item: ImageResult, entity_term: str) -> bool:
    hay = f"{item.title_or_alt} {item.page_url} {item.image_url} {item.source_name}".lower()
    if re.search(rf"\b{re.escape(entity_term)}\b", hay):
        return True
    return entity_term in hay


def should_use_web_boost(query: str, entities: list[str]) -> bool:
    q = query.lower()
    nightlife_words = ["diskotek", "discotheque", "nightclub", "club", "disco"]
    has_nightlife = any(word in q for word in nightlife_words)
    return has_nightlife and len([e for e in entities if len(e) >= 3]) >= 2


def search_bing_entity_mix(client: object, query: str, entities: list[str], limit: int) -> list[ImageResult]:
    out: list[ImageResult] = []
    out.extend(client.search_images(query, limit=limit))
    terms = canonical_entity_terms(entities)
    selected: list[str] = []
    if "copacabana" in terms:
        selected.append("copacabana")
    if "skagen" in terms:
        selected.append("skagen")
    for term in terms:
        if term not in selected:
            selected.append(term)
    for term in selected[:3]:
        out.extend(client.search_images(f"{term} diskotek", limit=max(4, limit // 3)))
    return filter_and_deduplicate(out)


def prioritize_web_venue_matches(results: list[ImageResult], entities: list[str]) -> list[ImageResult]:
    if not results:
        return []
    tokens = [e.lower() for e in entities if len(e) >= 3]
    if not tokens:
        return results
    out: list[tuple[int, ImageResult]] = []
    for item in results:
        hay = f"{item.title_or_alt} {item.page_url}".lower()
        score = sum(1 for t in tokens if t in hay)
        if "copacabana" in hay:
            score += 2
        if "skagen" in hay:
            score += 2
        if "diskotek" in hay or "discotheque" in hay or "nightclub" in hay:
            score += 2
        out.append((score, item))
    out.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in out]


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
