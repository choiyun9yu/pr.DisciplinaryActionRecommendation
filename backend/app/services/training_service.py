from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Union

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.metrics import f1_score
from sklearn.model_selection import StratifiedKFold
from sklearn.neighbors import KNeighborsClassifier

from app.core.text_utils import (
    ACTION_META,
    REQUIRED_COLUMNS,
    build_case_text,
    choose_primary_action,
    extract_action_components,
    normalize_text,
    validate_required_columns,
)
from app.models.domain import Artifacts


DEFAULT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
SCHEMA_VERSION = "2.0.0"


@lru_cache(maxsize=2)
def get_encoder(model_name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(model_name)


def read_table(path: Union[str, Path]) -> pd.DataFrame:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path)
    raise ValueError(f"지원하지 않는 파일 형식입니다: {suffix}")


def prepare_cases(path: Union[str, Path]) -> pd.DataFrame:
    df = read_table(path).copy()
    validate_required_columns(df.columns)

    lower_map = {col.lower(): col for col in df.columns}
    resolved_columns = [lower_map[col] for col in REQUIRED_COLUMNS]
    df = df.copy()

    # 필수 컬럼만 기준으로 정규화하되, 원본에 다른 컬럼이 있어도 보존 가능
    df["audit_source"] = df[resolved_columns[0]].apply(lambda x: normalize_text(x) or "미입력")
    df["finding_title"] = df[resolved_columns[1]].apply(normalize_text)
    df["finding_detail"] = df[resolved_columns[2]].apply(normalize_text)
    df["action_raw"] = df[resolved_columns[3]].apply(normalize_text)

    df["case_id"] = np.arange(1, len(df) + 1)
    df["action_components"] = df["action_raw"].apply(extract_action_components)
    df["action_norm"] = df["action_raw"].apply(choose_primary_action)
    df["text"] = df.apply(
        lambda row: build_case_text(row["finding_title"], row["finding_detail"]),
        axis=1,
    )
    df["action_group"] = df["action_norm"].map(lambda x: ACTION_META[x]["group"] if x else None)
    df["action_rank"] = df["action_norm"].map(lambda x: ACTION_META[x]["rank"] if x else None)
    df["action_components_str"] = df["action_components"].apply(lambda values: ", ".join(values))

    df = df[df["action_norm"].notna()].copy()
    df = df[df["text"].str.len() > 0].copy()

    ordered_columns = [
        "case_id",
        "audit_source",
        "finding_title",
        "finding_detail",
        "text",
        "action_raw",
        "action_norm",
        "action_group",
        "action_rank",
        "action_components_str",
    ]
    remaining = [col for col in df.columns if col not in ordered_columns]
    df = df[ordered_columns + remaining].reset_index(drop=True)
    return df


def build_embeddings(texts: list[str], model_name: str) -> np.ndarray:
    model = get_encoder(model_name)
    vectors = model.encode(
        texts,
        batch_size=32,
        show_progress_bar=len(texts) >= 64,
        convert_to_numpy=True,
        normalize_embeddings=False,
    )
    return np.asarray(vectors, dtype=np.float32)


def select_best_k(X: np.ndarray, y: np.ndarray) -> int:
    n_samples = len(y)
    if n_samples < 8:
        return max(1, min(3, n_samples))

    class_counts = pd.Series(y).value_counts()
    min_count = int(class_counts.min())
    if min_count < 2:
        return min(5, n_samples)

    n_splits = min(5, min_count)
    candidates = [k for k in [3, 5, 7, 9, 11] if k < n_samples]
    if not candidates:
        return min(5, n_samples)

    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
    best_k = candidates[0]
    best_score = -1.0

    for k in candidates:
        preds = np.empty(n_samples, dtype=object)
        for train_idx, test_idx in splitter.split(X, y):
            effective_k = min(k, len(train_idx))
            model = KNeighborsClassifier(
                n_neighbors=effective_k,
                weights="distance",
                metric="cosine",
                algorithm="brute",
                n_jobs=-1,
            )
            model.fit(X[train_idx], y[train_idx])
            preds[test_idx] = model.predict(X[test_idx])

        score = f1_score(y, preds, average="macro")
        if score > best_score:
            best_score = score
            best_k = k

    return best_k


def train_artifacts(cases: pd.DataFrame, model_name: str = DEFAULT_MODEL_NAME) -> Artifacts:
    embeddings = build_embeddings(cases["text"].tolist(), model_name=model_name)
    labels = cases["action_norm"].to_numpy()

    best_k = select_best_k(embeddings, labels)
    knn = KNeighborsClassifier(
        n_neighbors=best_k,
        weights="distance",
        metric="cosine",
        algorithm="brute",
        n_jobs=-1,
    )
    knn.fit(embeddings, labels)

    pca = PCA(n_components=2, random_state=42)
    pca.fit(embeddings)

    return Artifacts(
        cases=cases,
        embeddings=embeddings,
        knn=knn,
        pca=pca,
        model_name=model_name,
        best_k=best_k,
        trained_at=datetime.now(timezone.utc).isoformat(),
        schema_version=SCHEMA_VERSION,
        required_columns=REQUIRED_COLUMNS,
    )
