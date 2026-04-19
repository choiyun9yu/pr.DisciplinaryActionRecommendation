from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.controllers.recommendation_controller import router as recommendation_router
from app.controllers.training_controller import router as training_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="감사 지적 내용 기반 유사사례 검색 및 조치 추천 API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(recommendation_router)
app.include_router(training_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "message": "Audit Action Recommender API is running.",
        "health": f"{settings.api_prefix}/health",
        "training": f"{settings.api_prefix}/training/summary",
    }
