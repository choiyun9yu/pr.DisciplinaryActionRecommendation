from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class RecommendRequest(BaseModel):
    query: str = Field(..., min_length=3, description="자연어 지적 내용")
    top_k: int = Field(5, ge=3, le=20, description="표시할 유사사례 수")


class DistributionItem(BaseModel):
    action: str
    rank: int
    group: str
    count: Optional[int] = None
    probability: Optional[float] = None


class SourceDistributionItem(BaseModel):
    audit_source: str
    count: int


class NeighborItem(BaseModel):
    case_id: int
    rank: int
    similarity: float
    action_norm: str
    action_group: str
    action_raw: str
    audit_source: str
    finding_title: str
    finding_detail: str
    text: str


class ScatterItem(BaseModel):
    x: float
    y: float
    kind: str
    action_norm: str
    rank: int
    similarity: float
    text: str
    audit_source: str
    case_id: Optional[int] = None
    finding_title: str = ""
    finding_detail: str = ""


class RecommendResponse(BaseModel):
    query: str
    predicted_action: str
    predicted_group: str
    predicted_probability: float
    confidence_band: str
    top_similarity: float
    review_flags: list[str]
    count_distribution: list[DistributionItem]
    probability_distribution: list[DistributionItem]
    source_distribution: list[SourceDistributionItem]
    neighbors: list[NeighborItem]
    scatter: list[ScatterItem]


class HealthResponse(BaseModel):
    status: str
    num_cases: int = 0
    best_k: int = 0
    model_name: str = ""
    trained_at: str = ""
    schema_version: str = ""
    required_columns: list[str] = []
    message: Optional[str] = None


class CaseWritePayload(BaseModel):
    audit_source: str = Field(..., min_length=1, max_length=200)
    finding_title: str = Field(..., min_length=1, max_length=500)
    finding_detail: str = Field(..., min_length=1, max_length=4000)
    action: str = Field(..., min_length=1, max_length=200)


class CaseRow(BaseModel):
    row_id: int
    audit_source: str
    finding_title: str
    finding_detail: str
    action: str
    action_norm_preview: Optional[str] = None


class DatasetPageResponse(BaseModel):
    items: list[CaseRow]
    total: int
    page: int
    page_size: int
    total_pages: int
    available_actions: list[str]
    available_sources: list[str]


class DatasetSummaryResponse(BaseModel):
    dataset_path: str
    num_cases: int
    unique_audit_sources: int
    unique_actions: int
    last_modified_at: str
    artifact_ready: bool
    artifact_trained_at: str = ""
    artifact_best_k: int = 0
    artifact_model_name: str = ""
    needs_retrain: bool
    message: Optional[str] = None


class DatasetMutationResponse(BaseModel):
    message: str
    num_cases: int
    row_id: Optional[int] = None


class ImportResponse(BaseModel):
    message: str
    imported_count: int
    total_count: int
    mode: Literal["append", "replace"]


class RetrainResponse(BaseModel):
    message: str
    num_cases: int
    best_k: int
    model_name: str
    trained_at: str
