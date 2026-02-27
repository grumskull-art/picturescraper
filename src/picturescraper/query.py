from __future__ import annotations

import re
from itertools import combinations

from picturescraper.models import QueryAnalysis

YEAR_RE = re.compile(r"\b(19\d{2}|20\d{2})\b")
RANGE_RE = re.compile(r"\b(19\d{2}|20\d{2})\s*[-/]\s*(19\d{2}|20\d{2})\b")


def analyze_query(query: str, max_year_span: int = 15) -> QueryAnalysis:
    clean_query = " ".join(query.split())
    date_range = extract_date_range(clean_query)
    entities = extract_entities(clean_query)
    keywords = generate_search_keywords(entities, date_range, max_year_span=max_year_span)
    return QueryAnalysis(entities=entities, date_range=date_range, keywords=keywords)


def extract_date_range(query: str) -> tuple[int, int] | None:
    if match := RANGE_RE.search(query):
        start, end = int(match.group(1)), int(match.group(2))
        if start > end:
            start, end = end, start
        return (start, end)

    years = [int(y) for y in YEAR_RE.findall(query)]
    if not years:
        return None
    if len(years) == 1:
        return (years[0], years[0])
    years.sort()
    return (years[0], years[-1])


def extract_entities(query: str) -> list[str]:
    without_range = RANGE_RE.sub(" ", query)
    without_years = YEAR_RE.sub(" ", without_range)
    tokens = re.findall(r"[A-Za-z0-9]+", without_years)
    return tokens


def generate_search_keywords(
    entities: list[str],
    date_range: tuple[int, int] | None,
    max_year_span: int = 15,
) -> list[str]:
    clean_entities = [e.strip() for e in entities if e.strip()]
    base = " ".join(clean_entities).strip()
    if not base:
        return []

    phrase_variants = _build_phrase_variants(clean_entities)
    years = _sample_years(date_range, max_year_span=max_year_span)

    out: list[str] = list(phrase_variants)
    for phrase in phrase_variants[:4]:
        for year in years:
            out.append(f"{phrase} {year}")

    # Keep API calls bounded.
    return _dedupe_preserve_order(out)[:16]


def _build_phrase_variants(entities: list[str]) -> list[str]:
    variants = [" ".join(entities)]

    # Single-entity fallbacks can rescue difficult combined queries.
    if len(entities) > 1:
        variants.extend(entities)

    if len(entities) >= 2:
        # Add short pairwise combinations to avoid over-constrained multi-entity queries.
        for left, right in combinations(entities, 2):
            variants.append(f"{left} {right}")

        # Add merged adjacent tokens (e.g. "copa cabana" -> "copacabana").
        for i in range(len(entities) - 1):
            merged = entities.copy()
            merged[i : i + 2] = [f"{entities[i]}{entities[i + 1]}"]
            variants.append(" ".join(merged))
            variants.append(f"{entities[i]}{entities[i + 1]}")

    return _dedupe_preserve_order(variants)


def _sample_years(date_range: tuple[int, int] | None, max_year_span: int) -> list[int]:
    if date_range is None:
        return []
    start, end = date_range
    span = end - start + 1
    if span <= max_year_span:
        return list(range(start, end + 1))
    middle = start + (end - start) // 2
    return [start, middle, end]


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        clean = " ".join(item.split())
        if not clean:
            continue
        low = clean.lower()
        if low in seen:
            continue
        seen.add(low)
        out.append(clean)
    return out
