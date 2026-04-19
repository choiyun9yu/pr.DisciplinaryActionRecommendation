from __future__ import annotations

from functools import lru_cache

from app.core.config import get_settings
from app.services.dataset_service import DatasetService
from app.services.recommendation_service import RecommendationService


@lru_cache(maxsize=1)
def get_recommendation_service() -> RecommendationService:
    settings = get_settings()
    return RecommendationService(artifact_dir=settings.artifact_dir)


@lru_cache(maxsize=1)
def get_dataset_service() -> DatasetService:
    settings = get_settings()
    return DatasetService(dataset_path=settings.dataset_path, artifact_dir=settings.artifact_dir)
