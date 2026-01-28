# Kestra Workflows

현재 `kestra/` 폴더 안의 파일 기준으로 정리된 문서입니다. (흐름/설정/실행 방법 모두 실제 파일에 맞춤)

## 구성

`kestra/docker-compose.yml` 기준:
- `postgres` + `kestra` 컨테이너로 구성
- UI: `http://localhost:8080`
- 기본 계정: `admin@kestra.io` / `Admin1234`
- 플로우는 `kestra/flows` 폴더를 자동 로드

## 현재 구현된 Flows

### 1) `flows/gcp_kv.yaml`
- Flow ID: `04_gcp_kv`
- GCP 관련 KV 값 세팅
  - `GCP_PROJECT_ID`: `clickstream-pipeline-484705`
  - `GCP_LOCATION`: `US`
  - `GCP_BUCKET_NAME`: `clickstream-pipeline-484705-clickstream-data`
  - `GCP_DATASET`: `clickstream`

### 2) `flows/csv_gcs_load.yml`
- Flow ID: `csv_gcs_load`
- Kaggle 데이터셋 다운로드 후 GCS로 업로드
  - 데이터셋: `zynicide/wine-reviews`
  - 출력 파일: `extracted/*.csv`
  - 업로드 대상: `gs://{{ kv('GCP_BUCKET_NAME') }}/test/raw/{{ filename }}`
- 필요한 KV/Secret
  - `KAGGLE_USERNAME`
  - `KAGGLE_API_KEY`
  - `GCP_CREDS` (서비스 계정 JSON 전체)
  - `GCP_PROJECT_ID`, `GCP_LOCATION`, `GCP_BUCKET_NAME` (위 `gcp_kv.yaml`로 세팅 가능)

## 실행 방법

```bash
# Kestra 시작
cd kestra
docker-compose up -d

# UI 접속
http://localhost:8080
```

## KV/Secret 설정 가이드 (요약)

Kestra UI에서 아래 값이 있어야 `csv_gcs_load`가 동작합니다.
- `KAGGLE_USERNAME`, `KAGGLE_API_KEY`
- `GCP_CREDS` (서비스 계정 JSON 전체)
- GCP 기본 정보는 `gcp_kv.yaml` 실행으로 세팅 가능

## 참고

현재 repo의 Kestra 플로우는 **Kaggle → GCS 업로드**까지만 포함되어 있습니다.  
Spark/BigQuery/dbt 연동 플로우는 아직 `kestra/flows/`에 없습니다.
