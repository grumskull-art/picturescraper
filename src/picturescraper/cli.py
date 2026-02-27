from __future__ import annotations

import argparse
import json

from picturescraper.clients.openverse import OpenverseClient
from picturescraper.config import settings
from picturescraper.service import PictureSearchService, to_json_dict


def main() -> None:
    parser = argparse.ArgumentParser(description="Search images from Openverse")
    parser.add_argument("query", nargs="?", help="Search query text")
    parser.add_argument("--limit", type=int, default=10, help="Maximum results to return")
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    query = args.query or input("Type your image query: ").strip()
    if len(query) < 2:
        raise SystemExit("Query must be at least 2 characters")

    openverse = OpenverseClient(
        endpoint=settings.openverse_endpoint,
        timeout_seconds=settings.request_timeout_seconds,
    )
    service = PictureSearchService(openverse_client=openverse)
    result = service.search(query, limit=args.limit)
    output = to_json_dict(result)
    if args.pretty:
        print(json.dumps(output, indent=2, ensure_ascii=False))
    else:
        print(json.dumps(output, ensure_ascii=False))


if __name__ == "__main__":
    main()
