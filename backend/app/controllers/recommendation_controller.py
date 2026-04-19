from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import get_settings
from app.core.service_locator import get_recommendation_service
from app.schemas.api import HealthResponse, RecommendRequest, RecommendResponse
from app.services.recommendation_service import RecommendationService

settings = get_settings()
router = APIRouter(prefix=settings.api_prefix, tags=["recommendation"])


@router.get("/health", response_model=HealthResponse)
def health(service: RecommendationService = Depends(get_recommendation_service)) -> HealthResponse:
    return service.health()


@router.post("/recommend", response_model=RecommendResponse)
def recommend(
    payload: RecommendRequest,
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendResponse:
    try:
        return service.recommend(query=payload.query, top_k=payload.top_k)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
