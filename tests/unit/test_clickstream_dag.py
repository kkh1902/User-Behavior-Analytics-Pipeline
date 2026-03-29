from __future__ import annotations

import pytest
from airflow.models import DagBag
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

pytestmark = pytest.mark.unit


def _load_dagbag() -> DagBag:
    # DAG loading is the common entry point reused across all tests.
    return DagBag(dag_folder="airflow/dags", include_examples=False)


def _get_loaded_dag(dag_id: str):
    # get_dag() may trigger a meta-DB lookup depending on the environment, so use in-memory load results directly.
    return _load_dagbag().dags.get(dag_id)


def test_all_dag_files_import_cleanly() -> None:
    # Import errors make DAGs invisible to the scheduler, so catching them is the top priority.
    dagbag = _load_dagbag()
    assert dagbag.import_errors == {}, f"Import errors: {dagbag.import_errors}"


def test_expected_dags_exist_and_have_base_config() -> None:
    # In CI, validate base config only for the core operational DAGs (transform/modelling).
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
    # Monthly Spark transform tasks must have no upstream so they can run independently in parallel.
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
    # The pipeline DAG must run BQ DDL first, then dbt run, then dbt test in order.
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
