from picturescraper.query import analyze_query, extract_date_range, generate_search_keywords


def test_extract_date_range_single_year() -> None:
    assert extract_date_range("Copacabana 2001") == (2001, 2001)


def test_extract_date_range_range_swapped() -> None:
    assert extract_date_range("Skagen 2005-1995") == (1995, 2005)


def test_generate_keywords_capped_large_span() -> None:
    keywords = generate_search_keywords(["A", "B"], (1990, 2020), max_year_span=5)
    assert "A B 1990" in keywords
    assert "A B 2005" in keywords
    assert "A B 2020" in keywords
    assert "A B" in keywords


def test_analyze_query_entities_and_keywords() -> None:
    analysis = analyze_query("Copacabana Skagen 1995-1997")
    assert analysis.entities == ["Copacabana", "Skagen"]
    assert "Copacabana Skagen 1995" in analysis.keywords
    assert "Copacabana Skagen 1996" in analysis.keywords
    assert "Copacabana Skagen 1997" in analysis.keywords


def test_generate_keywords_has_relaxed_variants() -> None:
    keywords = generate_search_keywords(["Copa", "cabana", "Skagen"], (1994, 2010))
    assert "Copa cabana Skagen 1994" in keywords
    assert "Copacabana Skagen" in keywords
    assert "Skagen" in keywords
