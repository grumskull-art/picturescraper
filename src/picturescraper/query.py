from __future__ import annotations

import re

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
    base = " ".join(entities).strip()
    if not base:
        return []

    if date_range is None:
        return [base]

    start, end = date_range
    span = end - start + 1
    if span <= max_year_span:
        return [f"{base} {year}" for year in range(start, end + 1)]

    middle = start + (end - start) // 2
    return [f"{base} {start}", f"{base} {middle}", f"{base} {end}", base]
