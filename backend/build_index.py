from __future__ import annotations

import argparse
from pathlib import Path

from app.core.config import get_settings
from app.models.repository import ArtifactRepository
from app.services.training_service import DEFAULT_MODEL_NAME, prepare_cases, train_artifacts


def main() -> None:
    settings = get_settings()

    parser = argparse.ArgumentParser(description="감사 지적/조치 추천용 임베딩 인덱스를 생성합니다.")
    parser.add_argument("--input", required=True, help="학습 데이터 파일 경로 (.csv, .xlsx)")
    parser.add_argument("--out", default=settings.artifact_dir, help="아티팩트 저장 폴더")
    parser.add_argument("--model", default=DEFAULT_MODEL_NAME, help="SentenceTransformer 모델 이름 또는 로컬 경로")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.out)

    cases = prepare_cases(input_path)
    if len(cases) < 5:
        raise ValueError("학습 가능한 최소 데이터가 너무 적습니다. 최소 5건 이상 필요합니다.")

    print(f"[1/3] 데이터 정제 완료: {len(cases)}건")
    print(cases[["case_id", "audit_source", "finding_title", "action_raw", "action_norm"]].head())

    artifacts = train_artifacts(cases, model_name=args.model)
    print(f"[2/3] 임베딩 및 kNN 학습 완료: best_k={artifacts.best_k}")

    repository = ArtifactRepository(output_dir)
    repository.save(artifacts)
    print(f"[3/3] 저장 완료: {output_dir.resolve()}")


if __name__ == "__main__":
    main()
