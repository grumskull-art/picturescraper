from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    openverse_endpoint: str = os.getenv(
        "OPENVERSE_ENDPOINT", "https://api.openverse.org/v1/images/"
    )
    request_timeout_seconds: float = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "10"))
    max_year_span: int = int(os.getenv("MAX_YEAR_SPAN", "15"))
    collections_path: str = os.getenv("COLLECTIONS_PATH", "data/collections.json")


settings = Settings()
