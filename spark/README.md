# Spark Processing

GCS raw CSV를 읽어서 Parquet으로 변환하고 `processed/` 경로에 저장한다.

## 입력/출력 경로

- 입력: `gs://<bucket>/clickstream/raw/year=2019/month=<MM>/2019-<MM>.csv`
- 출력: `gs://<bucket>/clickstream/processed/year=2019/month=<MM>/event_date=YYYY-MM-DD/event_hour=H/part-*.parquet`

## 처리 요약

1. GCS raw CSV 다운로드
2. Spark로 CSV 읽기
3. `event_time`을 `event_ts`로 파싱 후 `event_date`, `event_hour` 컬럼 생성
4. `event_date`, `event_hour` 기준 파티션 Parquet 저장
5. GCS `processed/`에 업로드

## 실행 방법

1. Spark Docker 환경을 준비한다.
2. `spark/` 아래 ipynb 1개로 처리 로직을 실행한다.

## 해야할 것

- `spark/Dockerfile` 생성 (PySpark + Jupyter + 의존성 포함)
- `spark/docker-compose.yml` 생성 (노트북 포트와 볼륨 마운트 설정)
- 이미지 빌드 및 컨테이너 실행
