# 감사 지적 내용 기반 조치 추천기 (Docker Compose + 학습 데이터 관리 화면 포함)

이 패키지는 우리가 함께 만든 **React(View) + FastAPI(Controller / Model / Service)** 기반 프로젝트를
`docker compose`로 바로 올릴 수 있게 정리한 배포용 구조입니다.

이번 버전에는 기존 추천 페이지에 더해, **학습 전용 관리 페이지**가 새로 포함되어 있습니다.
이제 `audit_source,finding_title,finding_detail,action` CSV를 손으로 직접 만들지 않아도,
브라우저에서 사례를 **추가 / 수정 / 삭제 / 검색 / 가져오기 / 내보내기 / 재학습** 할 수 있습니다.

## 핵심 기능

- 고정 입력 스키마: `audit_source,finding_title,finding_detail,action`
- `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` 기반 dense embedding
- 코사인 거리 기반 최근접 검색
- 거리 가중 kNN 추천
- 최근접 사례 표 / 조치 분포 / 감사출처 분포 / PCA 2차원 분포 제공
- 질의 마커(마름모) / 유사사례 마커(원형) / 툴팁 상세 설명 제공
- **학습 데이터 관리 화면**
  - 사례 직접 입력
  - 사례 수정 / 삭제
  - CSV / Excel 가져오기 (append / replace)
  - 현재 데이터셋 CSV 내보내기
  - 재학습 실행
  - 재학습 필요 여부 표시

## 디렉터리 구조

```text
.
├─ docker-compose.yml
├─ .env.example
├─ data/
│  └─ audit_cases.csv
├─ artifacts/
├─ backend/
│  ├─ Dockerfile
│  ├─ docker-entrypoint.sh
│  ├─ requirements.txt
│  ├─ build_index.py
│  └─ app/
├─ frontend/
│  ├─ Dockerfile
│  ├─ nginx.conf
│  └─ src/
└─ sample_audit_cases.csv
```

## 실행 전 준비

### 1) 환경변수 파일 준비

```bash
cp .env.example .env
```

### 2) 데이터 파일은 없어도 됨

이 버전은 `data/audit_cases.csv`가 없더라도 백엔드가 **빈 CSV를 자동 생성**합니다.
즉, 처음에는 데이터 파일이 없어도 컨테이너를 띄운 뒤 학습 관리 화면에서 사례를 입력하면 됩니다.

물론 기존 CSV가 있다면 `data/audit_cases.csv`에 넣어두면 바로 반영됩니다.

필수 컬럼은 아래 네 개입니다.

```csv
audit_source,finding_title,finding_detail,action
2024 안동사업소 종합감사,법인카드 부정집행,계정과목 특근식비로 주류 구매,시정
2024 인사부 특정감사,관리감독 소홀,인사위원회 절차 관련 관리감독을 수행하지 못한 귀책이 인정됨,경고
```

## 실행

```bash
docker compose up --build
```

실행 후 접속 주소:

- 프론트엔드: `http://localhost:8080`
- 백엔드 API: `http://localhost:8000`
- 헬스체크: `http://localhost:8000/api/v1/health`

## 화면 구성

### 1) 추천 페이지

- 자연어 지적사항 입력
- 유사 사례 검색
- 조치 추천
- 조치 분포 / 확률 / 감사출처 / PCA 2차원 분포 표시

### 2) 학습 데이터 관리 페이지

브라우저 주소는 프론트에서 아래 해시 라우트로 구분됩니다.

- 추천 페이지: `http://localhost:8080/#/recommend`
- 학습 데이터 관리: `http://localhost:8080/#/training`

학습 데이터 관리 화면에서 가능한 작업:

- 사례 직접 입력
- 기존 사례 수정 / 삭제
- CSV / Excel 파일 가져오기
- 현재 데이터 CSV 내보내기
- 재학습 실행
- 현재 아티팩트가 최신인지, 재학습이 필요한지 확인

## 동작 방식

1. 백엔드 컨테이너 시작
2. `data/audit_cases.csv`가 없으면 빈 CSV 생성
3. `artifacts/metadata.json` 이 없거나, `data/audit_cases.csv`가 더 최신이면 재학습 후보로 판단
4. 데이터가 **5건 이상**이면 임베딩 / kNN / PCA 아티팩트 자동 생성
5. 데이터가 5건 미만이면 서버는 그대로 뜨고, 학습 관리 화면에서 사례를 더 넣은 뒤 수동으로 재학습 가능
6. 프론트엔드는 nginx가 정적 파일을 서빙하고 `/api/v1` 요청을 backend로 프록시

즉 **처음 한 번은 모델 다운로드와 임베딩 생성 때문에 시간이 걸릴 수 있지만**,
그 다음부터는 저장된 `artifacts/`와 Hugging Face 캐시를 재사용합니다.

## 데이터 교체 후 다시 학습시키는 방법

### 방법 1: 학습 데이터 관리 화면에서 수정 후 재학습

가장 권장하는 방법입니다.

- `#/training` 화면에서 사례를 관리
- `재학습 실행` 버튼 클릭
- 최신 아티팩트로 즉시 반영

### 방법 2: CSV를 바꾸고 재시작

`data/audit_cases.csv`를 교체한 뒤 다시 올리면,
CSV 파일 수정 시간이 `artifacts/metadata.json`보다 최신일 때 자동으로 재학습합니다.

```bash
docker compose down
docker compose up --build
```

### 방법 3: 강제 재학습

`.env`에서 아래 값을 1로 바꾼 뒤 다시 올립니다.

```env
FORCE_REBUILD_ARTIFACTS=1
```

재학습이 끝나면 다시 `0`으로 되돌리는 것을 권장합니다.

## 종료

```bash
docker compose down
```

모델 캐시와 생성된 아티팩트까지 모두 지우려면:

```bash
docker compose down -v
rm -rf artifacts/*
```

## 참고

- 현재 구조는 **Vector DB 없이 파일 아티팩트(`artifacts/`)를 영속 저장소처럼 사용하는 방식**입니다.
- 따라서 백엔드 컨테이너가 내려가도 아티팩트 파일이 남아 있는 한 임베딩과 모델은 유지됩니다.
- 학습 데이터 원본은 `data/audit_cases.csv`에 저장됩니다.
- 수백 건 규모에서는 현재 구조로도 충분히 실용적입니다.
- 데이터가 더 커지면 FAISS / Qdrant / pgvector 같은 벡터 인덱스로 확장할 수 있습니다.
