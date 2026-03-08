# 클릭스트림 파이프라인 포트폴리오 PPT 생성 프롬프트 (구현 내역 누락 금지 버전)

아래 요구사항으로 한국어 발표용 PPT를 만들어줘.
핵심: **실제 구현된 내용이 빠지면 안 된다.**

## 1) 발표 조건
- 목적: 데이터 엔지니어 포트폴리오 면접 발표
- 시간: 7~10분
- 슬라이드: 10장
- 구조: 모든 장에서 `문제 -> 해결 -> 성과` 흐름 유지

## 2) 출력 형식(각 슬라이드 공통)
- 제목 1개
- 핵심 bullet 4~6개
- 시각 요소 제안 1개
- 발표자 노트 3~5문장

## 3) 반드시 포함할 "구현 완료" 항목 체크리스트
아래 항목은 슬라이드 어딘가가 아니라, 논리 흐름에 맞춰 명시적으로 포함할 것.

### A. 오케스트레이션/Airflow
- DAG 3개 이름과 역할을 정확히 표기
  - `clickstream_ingest_raw`: Kaggle download -> unzip -> GCS upload
  - `clickstream_spark_transform`: Spark job 업로드 후 Dataproc 월별(10/11) 실행
  - `clickstream_pipeline`: BigQuery DDL -> `dbt run` -> `dbt test`
- 실패 알림: Slack webhook 콜백

### B. Spark 변환
- 파일: `spark/jobs/csv_parquet_job.py`
- 핵심 구현:
  - Bronze 문자열 스키마 로딩
  - 타입 캐스팅 실패 탐지 및 `failure_reason` 라벨링
  - 유효 행 정제 후 Processed 스키마 강제
  - `event_month`, `event_date`, `event_month_date` 생성
  - Parquet(Snappy) 저장
  - 대상 월 파티션 정리 후 append 적재

### C. BigQuery
- SQL 3종 실행 사실 명시:
  - `create_external_table.sql`
  - `create_partitioned_table.sql`
  - `create_partitioned_clustered_table.sql`

### D. dbt 모델
- 모델 4개 이름과 역할을 정확히 표기:
  - `stg_clickstream`
  - `fct_funnel_events`
  - `mart_funnel`
  - `mart_daily_funnel_kpi`
- 전환 KPI 3종 포함:
  - `view_to_cart_rate`
  - `cart_to_purchase_rate`
  - `overall_conversion_rate`

### E. 테스트/품질
- 구현된 테스트:
  - unit: DAG 구조 검증, Spark 변환 함수 검증
  - integration: Spark 변환 샘플 E2E
  - dbt test: `accepted_values`, `not_null`
- 미구현 항목도 정직하게 표기:
  - load/resilience/performance 테스트는 TODO(현재 skip)

### F. 인프라
- Terraform으로 GCS bucket, BigQuery dataset 프로비저닝 명시

## 4) 슬라이드별 요구사항
1. 프로젝트 개요
2. 문제 정의/KPI
3. 아키텍처
4. Airflow 3개 DAG 구현
5. Spark 변환 로직
6. BigQuery DDL + 적재 전략
7. dbt 모델 4개
8. 테스트/품질 현황(구현 vs TODO)
9. Looker Studio 대시보드와 인사이트
10. 한계/개선 로드맵

## 5) 작성 규칙
- 실제 파일/모델/DAG 이름을 정확히 쓸 것
- 없는 기능을 있는 것처럼 쓰지 말 것
- 수치가 확정되지 않은 경우 임의 수치 생성 금지
- 문체는 과장 없는 실무형
