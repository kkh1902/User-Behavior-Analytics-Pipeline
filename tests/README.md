# Tests Guide

이 디렉터리는 실행 단계 기준으로 테스트를 분리합니다.

## Directory Layout

- `unit/`
  - 빠르고 독립적인 테스트
  - 현재 파일:
    - `test_clickstream_dag.py`
    - `test_spark_csv_parquet_job.py`
- `integration/`
  - 컴포넌트 조합 검증(샘플 데이터 기반 E2E)
- `resilience/`
  - 장애/복구 시나리오(재시도, idempotency, 실패 분기)
- `load/`
  - 처리량/부하 시나리오(중간 규모 입력)
- `performance/`
  - 실행 시간/SLA/비용 회귀 검증
- `fixtures/`
  - 테스트 입력 및 기대 결과 샘플

## Local Run

### Unit DAG tests
```bash
uv run --no-project --with pytest --with apache-airflow==2.9.0 --with apache-airflow-providers-apache-spark --with requests pytest -q tests/unit/test_clickstream_dag.py
```

### Unit Spark tests
```bash
uv run --no-project --with pytest --with pyspark==3.5.1 pytest -q tests/unit/test_spark_csv_parquet_job.py
```

### Lint (critical only)
```bash
uv run --no-project --with ruff ruff check --select E9,F63,F7,F82 airflow/dags spark/jobs tests
```

## CI Mapping

- `lint`: 치명적 문법/정의 오류 탐지
- `spark-unit-tests`: `pytest tests/unit/test_spark_csv_parquet_job.py`
- `dag-tests`: `pytest tests/unit/test_clickstream_dag.py`
- `integration-tests`: `pytest tests/integration`

## Scope

- 현재 CI는 `unit`과 `integration`만 실행합니다.
- `resilience/load/performance`는 템플릿 파일만 두고 `skip` 처리되어 실행되지 않습니다.
