# Tests Guide

This directory organises tests by execution stage.

## Directory Layout

- `unit/`
  - Fast, isolated tests
  - Current files:
    - `test_clickstream_dag.py`
    - `test_spark_csv_parquet_job.py`
- `integration/`
  - Component combination validation (sample-data-based E2E)
- `resilience/`
  - Failure/recovery scenarios (retries, idempotency, failure branches)
- `load/`
  - Throughput/load scenarios (medium-scale input)
- `performance/`
  - Execution time / SLA / cost regression checks
- `fixtures/`
  - Test input samples and expected output samples

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

- `lint`: detect critical syntax / definition errors
- `spark-unit-tests`: `pytest tests/unit/test_spark_csv_parquet_job.py`
- `dag-tests`: `pytest tests/unit/test_clickstream_dag.py`
- `integration-tests`: `pytest tests/integration`

## Scope

- CI currently runs only `unit` and `integration` tests.
- `resilience/load/performance` contain template files only and are marked `skip`.
