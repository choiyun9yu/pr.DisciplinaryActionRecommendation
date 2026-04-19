#!/usr/bin/env bash
set -euo pipefail

ARTIFACT_DIR="${ARTIFACT_DIR:-/app/artifacts}"
DATASET_PATH="${DATASET_PATH:-/app/data/audit_cases.csv}"
MODEL_NAME="${MODEL_NAME:-sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2}"
AUTO_BUILD_ARTIFACTS="${AUTO_BUILD_ARTIFACTS:-1}"
FORCE_REBUILD_ARTIFACTS="${FORCE_REBUILD_ARTIFACTS:-0}"
PORT="${PORT:-8000}"
UVICORN_WORKERS="${UVICORN_WORKERS:-1}"

mkdir -p "${ARTIFACT_DIR}"
mkdir -p "$(dirname "${DATASET_PATH}")"

if [[ ! -f "${DATASET_PATH}" ]]; then
  echo "[backend] 학습 데이터 파일이 없어 빈 CSV를 생성합니다: ${DATASET_PATH}"
  DATASET_PATH_FOR_INIT="${DATASET_PATH}" python - <<'PY'
import os
from pathlib import Path
import pandas as pd
path = Path(os.environ['DATASET_PATH_FOR_INIT'])
path.parent.mkdir(parents=True, exist_ok=True)
pd.DataFrame(columns=["audit_source", "finding_title", "finding_detail", "action"]).to_csv(path, index=False, encoding="utf-8-sig")
PY
fi

should_build=0
if [[ "${AUTO_BUILD_ARTIFACTS}" == "1" ]]; then
  if [[ "${FORCE_REBUILD_ARTIFACTS}" == "1" || ! -f "${ARTIFACT_DIR}/metadata.json" || "${DATASET_PATH}" -nt "${ARTIFACT_DIR}/metadata.json" ]]; then
    row_count=$(python - <<PY
from pathlib import Path
import pandas as pd
path = Path(r"${DATASET_PATH}")
try:
    df = pd.read_csv(path)
    print(len(df))
except Exception:
    print(0)
PY
)
    if [[ "${row_count}" -ge 5 ]]; then
      should_build=1
    else
      echo "[backend] 학습 데이터가 ${row_count}건이라 자동 재학습을 건너뜁니다. (최소 5건 필요)"
    fi
  fi
fi

if [[ "${should_build}" == "1" ]]; then
  echo "[backend] 아티팩트를 새로 생성합니다."
  python build_index.py --input "${DATASET_PATH}" --out "${ARTIFACT_DIR}" --model "${MODEL_NAME}"
else
  echo "[backend] 기존 아티팩트를 사용하거나, 학습 관리 화면에서 재학습을 실행하세요."
fi

exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT}" --workers "${UVICORN_WORKERS}"
