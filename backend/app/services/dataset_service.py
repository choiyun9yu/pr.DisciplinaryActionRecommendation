from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Literal

import pandas as pd

from app.core.text_utils import REQUIRED_COLUMNS, choose_primary_action, normalize_text, validate_required_columns
from app.models.repository import ArtifactRepository, DatasetRepository
from app.schemas.api import CaseWritePayload
from app.services.training_service import DEFAULT_MODEL_NAME, prepare_cases, read_table, train_artifacts


class DatasetService:
    def __init__(self, dataset_path: str, artifact_dir: str):
        self.dataset_repository = DatasetRepository(dataset_path)
        self.artifact_repository = ArtifactRepository(artifact_dir)
        self._lock = Lock()

    def _load_df(self) -> pd.DataFrame:
        df = self.dataset_repository.load().copy()
        if df.empty:
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
        for column in REQUIRED_COLUMNS:
            if column not in df.columns:
                df[column] = ""
        return df[REQUIRED_COLUMNS]

    def _save_df(self, df: pd.DataFrame) -> None:
        output = df.copy()
        for column in REQUIRED_COLUMNS:
            if column not in output.columns:
                output[column] = ""
        self.dataset_repository.save(output[REQUIRED_COLUMNS])

    def _normalize_payload(self, payload: CaseWritePayload) -> dict[str, str]:
        normalized = {
            "audit_source": normalize_text(payload.audit_source) or "미입력",
            "finding_title": normalize_text(payload.finding_title),
            "finding_detail": normalize_text(payload.finding_detail),
            "action": normalize_text(payload.action),
        }
        missing = [key for key in ["finding_title", "finding_detail", "action"] if not normalized[key]]
        if missing:
            raise ValueError(f"다음 필드는 비워둘 수 없습니다: {', '.join(missing)}")
        return normalized

    def _dataset_mtime_iso(self) -> str:
        self.dataset_repository.ensure_exists()
        dt = datetime.fromtimestamp(self.dataset_repository.dataset_path.stat().st_mtime, tz=timezone.utc)
        return dt.isoformat()

    def get_summary(self) -> dict:
        df = self._load_df()
        artifact_meta = self.artifact_repository.load_metadata()
        dataset_mtime = self.dataset_repository.dataset_path.stat().st_mtime if self.dataset_repository.dataset_path.exists() else 0.0
        artifact_mtime = self.artifact_repository.metadata_path().stat().st_mtime if self.artifact_repository.exists() else 0.0
        needs_retrain = not self.artifact_repository.exists() or dataset_mtime > artifact_mtime

        return {
            "dataset_path": str(self.dataset_repository.dataset_path.resolve()),
            "num_cases": int(len(df)),
            "unique_audit_sources": int(df["audit_source"].fillna("미입력").astype(str).str.strip().replace("", "미입력").nunique()) if len(df) else 0,
            "unique_actions": int(df["action"].fillna("").astype(str).str.strip().replace("", pd.NA).dropna().nunique()) if len(df) else 0,
            "last_modified_at": self._dataset_mtime_iso(),
            "artifact_ready": bool(self.artifact_repository.exists()),
            "artifact_trained_at": str((artifact_meta or {}).get("trained_at", "")),
            "artifact_best_k": int((artifact_meta or {}).get("best_k", 0) or 0),
            "artifact_model_name": str((artifact_meta or {}).get("model_name", "")),
            "needs_retrain": bool(needs_retrain),
            "message": None if len(df) >= 5 else "재학습을 하려면 최소 5건 이상의 사례가 필요합니다.",
        }

    def list_cases(
        self,
        search: str = "",
        action_filter: str = "",
        audit_source_filter: str = "",
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        df = self._load_df().copy()
        if len(df):
            df["row_id"] = range(1, len(df) + 1)
            df["action_norm_preview"] = df["action"].apply(choose_primary_action)
        else:
            df = pd.DataFrame(columns=["row_id", *REQUIRED_COLUMNS, "action_norm_preview"])

        search_norm = normalize_text(search).lower()
        if search_norm:
            mask = pd.Series(False, index=df.index)
            for column in ["audit_source", "finding_title", "finding_detail", "action"]:
                mask = mask | df[column].fillna("").astype(str).str.lower().str.contains(search_norm, regex=False)
            df = df[mask].copy()

        action_filter_norm = normalize_text(action_filter)
        if action_filter_norm:
            df = df[df["action_norm_preview"].fillna("") == action_filter_norm].copy()

        source_filter_norm = normalize_text(audit_source_filter)
        if source_filter_norm:
            df = df[df["audit_source"].fillna("") == source_filter_norm].copy()

        total = int(len(df))
        total_pages = max(1, (total + page_size - 1) // page_size)
        current_page = min(max(1, page), total_pages)
        start = (current_page - 1) * page_size
        end = start + page_size
        page_df = df.iloc[start:end].copy()

        base_df = self._load_df().copy()
        available_sources = sorted({normalize_text(value) or "미입력" for value in base_df.get("audit_source", pd.Series(dtype=str)).tolist() if normalize_text(value) or "미입력"})
        available_actions = sorted({value for value in base_df.get("action", pd.Series(dtype=str)).apply(choose_primary_action).dropna().tolist()})

        return {
            "items": page_df[["row_id", "audit_source", "finding_title", "finding_detail", "action", "action_norm_preview"]].to_dict(orient="records"),
            "total": total,
            "page": current_page,
            "page_size": page_size,
            "total_pages": total_pages,
            "available_actions": available_actions,
            "available_sources": available_sources,
        }

    def create_case(self, payload: CaseWritePayload) -> dict:
        with self._lock:
            df = self._load_df()
            normalized = self._normalize_payload(payload)
            updated = pd.concat([df, pd.DataFrame([normalized])], ignore_index=True)
            self._save_df(updated)
            return {
                "message": "사례를 추가했습니다. 재학습 전까지 추천 결과는 기존 아티팩트를 사용합니다.",
                "num_cases": int(len(updated)),
                "row_id": int(len(updated)),
            }

    def update_case(self, row_id: int, payload: CaseWritePayload) -> dict:
        with self._lock:
            df = self._load_df()
            if row_id < 1 or row_id > len(df):
                raise IndexError("수정할 사례를 찾을 수 없습니다.")
            normalized = self._normalize_payload(payload)
            for key, value in normalized.items():
                df.at[row_id - 1, key] = value
            self._save_df(df)
            return {
                "message": "사례를 수정했습니다. 재학습을 실행하면 추천 모델에 반영됩니다.",
                "num_cases": int(len(df)),
                "row_id": row_id,
            }

    def delete_case(self, row_id: int) -> dict:
        with self._lock:
            df = self._load_df()
            if row_id < 1 or row_id > len(df):
                raise IndexError("삭제할 사례를 찾을 수 없습니다.")
            updated = df.drop(index=row_id - 1).reset_index(drop=True)
            self._save_df(updated)
            return {
                "message": "사례를 삭제했습니다. 재학습 전까지 추천 결과는 기존 아티팩트를 사용합니다.",
                "num_cases": int(len(updated)),
                "row_id": None,
            }

    def import_cases(self, file_path: Path, mode: Literal["append", "replace"]) -> dict:
        imported = read_table(file_path)
        validate_required_columns(imported.columns)
        lower_map = {col.lower(): col for col in imported.columns}
        imported = imported[[lower_map[col] for col in REQUIRED_COLUMNS]].copy()
        imported.columns = REQUIRED_COLUMNS
        for column in REQUIRED_COLUMNS:
            imported[column] = imported[column].apply(lambda value: normalize_text(value) or ("미입력" if column == "audit_source" else ""))
        imported = imported[(imported["finding_title"] != "") & (imported["finding_detail"] != "") & (imported["action"] != "")].reset_index(drop=True)

        with self._lock:
            current = self._load_df()
            if mode == "append":
                updated = pd.concat([current, imported], ignore_index=True)
            else:
                updated = imported.copy()
            self._save_df(updated)

        return {
            "message": "CSV/XLSX 가져오기를 완료했습니다. 재학습을 실행하면 추천 모델에 반영됩니다.",
            "imported_count": int(len(imported)),
            "total_count": int(len(updated)),
            "mode": mode,
        }

    def rebuild_artifacts(self, model_name: str = DEFAULT_MODEL_NAME) -> dict:
        with self._lock:
            cases = prepare_cases(self.dataset_repository.dataset_path)
            if len(cases) < 5:
                raise ValueError("학습 가능한 최소 데이터가 너무 적습니다. 최소 5건 이상 필요합니다.")
            artifacts = train_artifacts(cases, model_name=model_name)
            self.artifact_repository.save(artifacts)
            return {
                "message": "재학습이 완료되었습니다.",
                "num_cases": int(len(cases)),
                "best_k": int(artifacts.best_k),
                "model_name": artifacts.model_name,
                "trained_at": artifacts.trained_at,
            }
