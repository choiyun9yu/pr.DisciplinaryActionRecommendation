from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Union

import joblib
import numpy as np
import pandas as pd
from pandas.errors import EmptyDataError

from app.core.text_utils import REQUIRED_COLUMNS, validate_required_columns
from app.models.domain import Artifacts


class ArtifactRepository:
    def __init__(self, artifact_dir: Union[str, Path]):
        self.artifact_dir = Path(artifact_dir)

    def _metadata_path(self) -> Path:
        return self.artifact_dir / "metadata.json"

    def _cases_path(self) -> Path:
        return self.artifact_dir / "cases_normalized.csv"

    def _embeddings_path(self) -> Path:
        return self.artifact_dir / "embeddings.npy"

    def _knn_path(self) -> Path:
        return self.artifact_dir / "knn.joblib"

    def _pca_path(self) -> Path:
        return self.artifact_dir / "pca.joblib"

    def save(self, artifacts: Artifacts) -> None:
        self.artifact_dir.mkdir(parents=True, exist_ok=True)

        artifacts.cases.to_csv(self._cases_path(), index=False, encoding="utf-8-sig")
        np.save(self._embeddings_path(), artifacts.embeddings)
        joblib.dump(artifacts.knn, self._knn_path())
        joblib.dump(artifacts.pca, self._pca_path())

        metadata = {
            "model_name": artifacts.model_name,
            "best_k": artifacts.best_k,
            "num_cases": int(len(artifacts.cases)),
            "labels": list(map(str, artifacts.knn.classes_)),
            "trained_at": artifacts.trained_at,
            "schema_version": artifacts.schema_version,
            "required_columns": artifacts.required_columns,
        }
        self._metadata_path().write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def exists(self) -> bool:
        return self._metadata_path().exists()

    def metadata_path(self) -> Path:
        return self._metadata_path()

    def load_metadata(self) -> dict[str, Any] | None:
        if not self._metadata_path().exists():
            return None
        return json.loads(self._metadata_path().read_text(encoding="utf-8"))

    def load(self) -> Artifacts:
        required_files = [
            self._metadata_path(),
            self._cases_path(),
            self._embeddings_path(),
            self._knn_path(),
            self._pca_path(),
        ]
        missing = [str(path) for path in required_files if not path.exists()]
        if missing:
            raise FileNotFoundError(
                "학습 아티팩트가 준비되지 않았습니다. 먼저 build_index.py를 실행하세요. "
                f"누락 파일: {missing}"
            )

        metadata = json.loads(self._metadata_path().read_text(encoding="utf-8"))
        return Artifacts(
            cases=pd.read_csv(self._cases_path()),
            embeddings=np.load(self._embeddings_path(), allow_pickle=False),
            knn=joblib.load(self._knn_path()),
            pca=joblib.load(self._pca_path()),
            model_name=str(metadata["model_name"]),
            best_k=int(metadata["best_k"]),
            trained_at=str(metadata.get("trained_at", "")),
            schema_version=str(metadata.get("schema_version", "1.0.0")),
            required_columns=list(metadata.get("required_columns", [])),
        )


class DatasetRepository:
    def __init__(self, dataset_path: Union[str, Path]):
        self.dataset_path = Path(dataset_path)

    def ensure_exists(self) -> None:
        self.dataset_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.dataset_path.exists():
            pd.DataFrame(columns=REQUIRED_COLUMNS).to_csv(self.dataset_path, index=False, encoding="utf-8-sig")

    def load(self) -> pd.DataFrame:
        self.ensure_exists()
        if self.dataset_path.suffix.lower() != ".csv":
            raise ValueError("학습 데이터셋 관리 페이지는 CSV 파일만 직접 편집할 수 있습니다.")
        if self.dataset_path.stat().st_size == 0:
            return pd.DataFrame(columns=REQUIRED_COLUMNS)

        try:
            df = pd.read_csv(self.dataset_path)
        except EmptyDataError:
            return pd.DataFrame(columns=REQUIRED_COLUMNS)
        if df.empty and len(df.columns) == 0:
            return pd.DataFrame(columns=REQUIRED_COLUMNS)

        validate_required_columns(df.columns)
        lower_map = {col.lower(): col for col in df.columns}
        ordered = [lower_map[col] for col in REQUIRED_COLUMNS]
        result = df[ordered].copy()
        result.columns = REQUIRED_COLUMNS
        return result

    def save(self, df: pd.DataFrame) -> None:
        self.ensure_exists()
        output = df.copy()
        output = output[REQUIRED_COLUMNS]
        output.to_csv(self.dataset_path, index=False, encoding="utf-8-sig")

    def last_modified_iso(self) -> str:
        self.ensure_exists()
        dt = datetime.fromtimestamp(self.dataset_path.stat().st_mtime, tz=timezone.utc)
        return dt.isoformat()
