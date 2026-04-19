from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    api_prefix: str
    artifact_dir: str
    dataset_path: str
    allowed_origins: list[str]
    allowed_origin_regex: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    backend_root = Path(__file__).resolve().parents[2]
    project_root = backend_root.parent
    default_artifact_dir = str((project_root / "artifacts").resolve())
    default_dataset_path = str((project_root / "data" / "audit_cases.csv").resolve())

    allowed_origins_raw = os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173,http://localhost:8080,http://127.0.0.1:8080",
    )
    allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]
    return Settings(
        app_name=os.getenv("APP_NAME", "Audit Action Recommender API"),
        app_version=os.getenv("APP_VERSION", "2.2.0"),
        api_prefix=os.getenv("API_PREFIX", "/api/v1"),
        artifact_dir=os.getenv("ARTIFACT_DIR", default_artifact_dir),
        dataset_path=os.getenv("DATASET_PATH", default_dataset_path),
        allowed_origins=allowed_origins,
        allowed_origin_regex=os.getenv("ALLOWED_ORIGIN_REGEX", r"https?://(localhost|127\.0\.0\.1)(:\d+)?$"),
    )
