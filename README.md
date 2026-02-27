# PictureScraper

Image search app that analyzes a free-text query, expands keywords, searches Openverse, and when needed performs Denmark-focused web scraping from curated Danish sources.

## Features
- Query analysis: entities + year or year-range extraction
- Openverse search with advanced filters:
  - `license` substring filter
  - `source` substring filter
  - `orientation` (`landscape|portrait|square`)
- Denmark-focused fallback scraping from curated sources:
  - `skagensavis.dk`
  - `tv2nord.dk`
  - `nordjyske.dk`
  - `dr.dk`
- Pagination support for infinite scroll UX
- Export current results as JSON or CSV
- Save and reload collections locally (`data/collections.json` by default)
- Two interfaces:
  - Browser UI (`/`)
  - REST API (`FastAPI`)
  - CLI tool
- Automated tests (`pytest`)

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
cp .env.example .env
```

## Run API

```bash
uvicorn picturescraper.api:app --reload --app-dir src
```

Web app:

```bash
open http://127.0.0.1:8000/
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Search:

```bash
curl 'http://127.0.0.1:8000/search?q=Copacabana%20Skagen%201995-2005&limit=12&page=1&orientation=landscape&source=wikimedia'
```

## Run CLI

```bash
PYTHONPATH=src python -m picturescraper.cli "Copacabana Skagen 1995-2005" --pretty
```

## API output format

```json
{
  "reasoning_steps": "...",
  "results": [
    {
      "image_url": "...",
      "page_url": "...",
      "title_or_alt": "...",
      "source_name": "Openverse source",
      "date_if_available": "...",
      "license": "...",
      "width": 1024,
      "height": 768
    }
  ],
  "page": 1,
  "limit": 12,
  "count": 12,
  "total_results": 104,
  "has_more": true,
  "next_page": 2
}
```

## Test

```bash
PYTHONPATH=src pytest -q
```
