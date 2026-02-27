# PictureScraper

Image search app that analyzes a free-text query, expands keywords, searches Openverse, deduplicates results, and returns reasoning + structured JSON.

## Features
- Query analysis: entities + year or year-range extraction
- Source search:
  - Openverse (no API key)
- Deduplication and basic quality ranking
- Two interfaces:
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

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Search:

```bash
curl 'http://127.0.0.1:8000/search?q=Copacabana%20Skagen%201995-2005&limit=10'
```

## Run CLI

```bash
PYTHONPATH=src python -m picturescraper.cli "Copacabana Skagen 1995-2005" --pretty
```

## Output format

```json
{
  "reasoning_steps": "...",
  "results": [
    {
      "image_url": "...",
      "page_url": "...",
      "title_or_alt": "...",
      "source_name": "Openverse",
      "date_if_available": "...",
      "license": "..."
    }
  ]
}
```

## Test

```bash
PYTHONPATH=src pytest -q
```
