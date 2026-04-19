from __future__ import annotations

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.service_locator import get_dataset_service, get_recommendation_service
from app.schemas.api import (
    CaseWritePayload,
    DatasetMutationResponse,
    DatasetPageResponse,
    DatasetSummaryResponse,
    ImportResponse,
    RetrainResponse,
)
from app.services.dataset_service import DatasetService
from app.services.recommendation_service import RecommendationService

settings = get_settings()
router = APIRouter(prefix=f"{settings.api_prefix}/training", tags=["training"])


@router.get("/summary", response_model=DatasetSummaryResponse)
def get_summary(service: DatasetService = Depends(get_dataset_service)) -> DatasetSummaryResponse:
    return DatasetSummaryResponse(**service.get_summary())


@router.get("/cases", response_model=DatasetPageResponse)
def list_cases(
    search: str = Query("", description="검색어"),
    action_filter: str = Query("", description="정규화 조치 필터"),
    audit_source_filter: str = Query("", description="감사출처 필터"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=5, le=100),
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetPageResponse:
    return DatasetPageResponse(
        **service.list_cases(
            search=search,
            action_filter=action_filter,
            audit_source_filter=audit_source_filter,
            page=page,
            page_size=page_size,
        )
    )


@router.post("/cases", response_model=DatasetMutationResponse)
def create_case(
    payload: CaseWritePayload,
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetMutationResponse:
    try:
        return DatasetMutationResponse(**service.create_case(payload))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.put("/cases/{row_id}", response_model=DatasetMutationResponse)
def update_case(
    row_id: int,
    payload: CaseWritePayload,
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetMutationResponse:
    try:
        return DatasetMutationResponse(**service.update_case(row_id, payload))
    except IndexError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.delete("/cases/{row_id}", response_model=DatasetMutationResponse)
def delete_case(
    row_id: int,
    service: DatasetService = Depends(get_dataset_service),
) -> DatasetMutationResponse:
    try:
        return DatasetMutationResponse(**service.delete_case(row_id))
    except IndexError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/import", response_model=ImportResponse)
async def import_cases(
    file: UploadFile = File(...),
    mode: str = Form("append"),
    service: DatasetService = Depends(get_dataset_service),
) -> ImportResponse:
    if mode not in {"append", "replace"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="mode 는 append 또는 replace 여야 합니다.")

    suffix = Path(file.filename or "dataset.csv").suffix.lower()
    if suffix not in {".csv", ".xlsx", ".xls"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV 또는 Excel 파일만 업로드할 수 있습니다.")

    with NamedTemporaryFile(delete=False, suffix=suffix) as temp:
        temp.write(await file.read())
        temp_path = Path(temp.name)

    try:
        result = service.import_cases(temp_path, mode=mode)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    finally:
        temp_path.unlink(missing_ok=True)

    return ImportResponse(**result)


@router.get("/export")
def export_cases(service: DatasetService = Depends(get_dataset_service)) -> FileResponse:
    service.dataset_repository.ensure_exists()
    return FileResponse(
        service.dataset_repository.dataset_path,
        media_type="text/csv",
        filename=service.dataset_repository.dataset_path.name,
    )


@router.post("/retrain", response_model=RetrainResponse)
def retrain(
    service: DatasetService = Depends(get_dataset_service),
    recommendation_service: RecommendationService = Depends(get_recommendation_service),
) -> RetrainResponse:
    try:
        result = service.rebuild_artifacts()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    recommendation_service.invalidate_cache()
    return RetrainResponse(**result)
