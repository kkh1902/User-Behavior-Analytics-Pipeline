from __future__ import annotations

import pytest
from airflow.models import DagBag
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

pytestmark = pytest.mark.unit


def _load_dagbag() -> DagBag:
    # DAG 로딩은 모든 테스트의 공통 진입점으로 재사용한다.
    return DagBag(dag_folder="airflow/dags", include_examples=False)


def _get_loaded_dag(dag_id: str):
    # get_dag()는 환경에 따라 메타DB 조회를 유발할 수 있어, 메모리 로드 결과를 직접 사용한다.
    return _load_dagbag().dags.get(dag_id)


def test_all_dag_files_import_cleanly() -> None:
    # import 에러가 있으면 스케줄러에서 DAG 자체가 보이지 않기 때문에 최우선으로 막는다.
    dagbag = _load_dagbag()
    assert dagbag.import_errors == {}, f"Import errors: {dagbag.import_errors}"


def test_expected_dags_exist_and_have_base_config() -> None:
    # CI에서 운영 핵심 DAG(변환/모델링)만 기본 설정을 검증한다.
    dagbag = _load_dagbag()
    expected_dags = {
        "clickstream_spark_transform",
        "clickstream_pipeline",
    }
    assert expected_dags.issubset(set(dagbag.dags.keys()))

    for dag_id in expected_dags:
        dag = dagbag.dags.get(dag_id)
        assert dag is not None
        assert dag.schedule_interval is None
        assert dag.catchup is False
        assert dag.default_args["retries"] == 1
        assert callable(dag.default_args["on_failure_callback"])


def test_spark_transform_dag_tasks_and_args() -> None:
    # 월별 Spark 변환 task가 병렬로 독립 실행 가능하도록 upstream이 없어야 한다.
    dag = _get_loaded_dag("clickstream_spark_transform")
    assert dag is not None

    expected_tasks = {"spark_csv_to_parquet_oct", "spark_csv_to_parquet_nov"}
    assert expected_tasks == set(dag.task_ids)

    spark_oct = dag.get_task("spark_csv_to_parquet_oct")
    spark_nov = dag.get_task("spark_csv_to_parquet_nov")

    assert isinstance(spark_oct, SparkSubmitOperator)
    assert isinstance(spark_nov, SparkSubmitOperator)

    assert spark_oct.upstream_task_ids == set()
    assert spark_nov.upstream_task_ids == set()
    assert "--month" in spark_oct.application_args
    assert "--month" in spark_nov.application_args
    assert "10" in spark_oct.application_args
    assert "11" in spark_nov.application_args


def test_pipeline_dag_tasks_and_dependencies() -> None:
    # 파이프라인 DAG은 BQ DDL 선행 후 dbt run/test 순으로 이어져야 한다.
    dag = _get_loaded_dag("clickstream_pipeline")
    assert dag is not None

    expected_tasks = {"create_bigquery_tables", "dbt_run", "dbt_test"}
    assert expected_tasks == set(dag.task_ids)

    create_bq = dag.get_task("create_bigquery_tables")
    dbt_run = dag.get_task("dbt_run")
    dbt_test = dag.get_task("dbt_test")

    assert isinstance(create_bq, PythonOperator)
    assert isinstance(dbt_run, BashOperator)
    assert isinstance(dbt_test, BashOperator)

    assert create_bq.downstream_task_ids == {"dbt_run"}
    assert dbt_run.upstream_task_ids == {"create_bigquery_tables"}
    assert dbt_test.upstream_task_ids == {"dbt_run"}
    assert "dbt run" in dbt_run.bash_command
    assert "dbt test" in dbt_test.bash_command
