from __future__ import annotations

import numpy as np
import pandas as pd

from app.core.text_utils import ACTION_META, ACTION_ORDER, REQUIRED_COLUMNS, normalize_text
from app.models.repository import ArtifactRepository
from app.schemas.api import HealthResponse, RecommendResponse
from app.services.training_service import get_encoder


def confidence_band(prob: float) -> str:
    if prob >= 0.80:
        return "높음"
    if prob >= 0.60:
        return "보통"
    return "낮음"


class RecommendationService:
    def __init__(self, artifact_dir: str):
        self.repository = ArtifactRepository(artifact_dir)
        self._artifacts = None

    def invalidate_cache(self) -> None:
        self._artifacts = None

    def get_artifacts(self):
        if self._artifacts is None:
            self._artifacts = self.repository.load()
        return self._artifacts

    def health(self) -> HealthResponse:
        try:
            artifacts = self.get_artifacts()
        except FileNotFoundError as exc:
            return HealthResponse(
                status="not_ready",
                message=str(exc),
                required_columns=REQUIRED_COLUMNS,
            )

        return HealthResponse(
            status="ready",
            num_cases=len(artifacts.cases),
            best_k=artifacts.best_k,
            model_name=artifacts.model_name,
            trained_at=artifacts.trained_at,
            schema_version=artifacts.schema_version,
            required_columns=artifacts.required_columns,
        )

    def recommend(self, query: str, top_k: int) -> RecommendResponse:
        artifacts = self.get_artifacts()
        encoder = get_encoder(artifacts.model_name)

        query_norm = normalize_text(query)
        query_vec = encoder.encode([query_norm], convert_to_numpy=True).astype(np.float32)

        k = min(top_k or artifacts.best_k, len(artifacts.cases))
        distances, indices = artifacts.knn.kneighbors(query_vec, n_neighbors=k, return_distance=True)
        probabilities = artifacts.knn.predict_proba(query_vec)[0]

        pred_idx = int(np.argmax(probabilities))
        pred_label = str(artifacts.knn.classes_[pred_idx])
        pred_prob = float(probabilities[pred_idx])

        neighbor_df = artifacts.cases.iloc[indices[0]].copy().reset_index(drop=True)
        neighbor_df["distance"] = distances[0]
        neighbor_df["similarity"] = 1.0 - neighbor_df["distance"]
        neighbor_df["rank"] = np.arange(1, len(neighbor_df) + 1)

        count_dist = (
            neighbor_df["action_norm"]
            .value_counts()
            .reindex(ACTION_ORDER)
            .dropna()
            .astype(int)
            .reset_index()
        )
        count_dist.columns = ["action", "count"]
        count_dist["rank"] = count_dist["action"].map(lambda value: ACTION_META[str(value)]["rank"])
        count_dist["group"] = count_dist["action"].map(lambda value: ACTION_META[str(value)]["group"])

        prob_dist = pd.DataFrame({"action": artifacts.knn.classes_, "probability": probabilities})
        prob_dist["rank"] = prob_dist["action"].map(lambda value: ACTION_META[str(value)]["rank"])
        prob_dist["group"] = prob_dist["action"].map(lambda value: ACTION_META[str(value)]["group"])
        prob_dist = prob_dist.sort_values(["probability", "rank"], ascending=[False, False]).reset_index(drop=True)

        source_dist = neighbor_df["audit_source"].fillna("미입력").value_counts().reset_index()
        source_dist.columns = ["audit_source", "count"]

        projected_neighbors = artifacts.pca.transform(artifacts.embeddings[indices[0]])
        projected_query = artifacts.pca.transform(query_vec)

        scatter_df = neighbor_df[
            [
                "case_id",
                "rank",
                "action_norm",
                "similarity",
                "finding_title",
                "finding_detail",
                "text",
                "audit_source",
            ]
        ].copy()
        scatter_df["x"] = projected_neighbors[:, 0]
        scatter_df["y"] = projected_neighbors[:, 1]
        scatter_df["kind"] = "neighbor"

        query_point = pd.DataFrame(
            {
                "case_id": [None],
                "rank": [0],
                "action_norm": [pred_label],
                "similarity": [1.0],
                "finding_title": ["입력 질의"],
                "finding_detail": [query_norm],
                "text": [query_norm],
                "audit_source": ["입력 질의"],
                "x": [float(projected_query[0, 0])],
                "y": [float(projected_query[0, 1])],
                "kind": ["query"],
            }
        )
        scatter_df = pd.concat([scatter_df, query_point], ignore_index=True)

        review_flags: list[str] = []
        top_similarity = float(neighbor_df["similarity"].max()) if len(neighbor_df) else 0.0
        if pred_prob < 0.55:
            review_flags.append("주변 사례들의 조치가 많이 갈립니다.")
        if top_similarity < 0.45:
            review_flags.append("매우 유사한 선례가 충분하지 않습니다.")
        if neighbor_df["action_norm"].nunique() >= max(3, k // 2):
            review_flags.append("최근접 이웃의 조치 분산이 큽니다.")

        return RecommendResponse(
            query=query_norm,
            predicted_action=pred_label,
            predicted_group=ACTION_META[pred_label]["group"],
            predicted_probability=pred_prob,
            confidence_band=confidence_band(pred_prob),
            top_similarity=top_similarity,
            review_flags=review_flags,
            count_distribution=count_dist.to_dict(orient="records"),
            probability_distribution=prob_dist.to_dict(orient="records"),
            source_distribution=source_dist.to_dict(orient="records"),
            neighbors=neighbor_df[
                [
                    "case_id",
                    "rank",
                    "similarity",
                    "action_norm",
                    "action_group",
                    "action_raw",
                    "audit_source",
                    "finding_title",
                    "finding_detail",
                    "text",
                ]
            ].to_dict(orient="records"),
            scatter=scatter_df[
                [
                    "x",
                    "y",
                    "kind",
                    "action_norm",
                    "rank",
                    "similarity",
                    "text",
                    "audit_source",
                    "case_id",
                    "finding_title",
                    "finding_detail",
                ]
            ].to_dict(orient="records"),
        )
