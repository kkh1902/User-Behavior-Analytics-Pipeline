from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

import requests
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

GCP_BUCKET = os.environ.get("GCP_BUCKET_NAME", "clickstream-pipeline-484705-clickstream-data")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "clickstream-pipeline-484705")
BQ_DATASET = os.environ.get("BQ_DATASET", "clickstream")
GCP_CREDS_PATH = "/cred/clickstream-sa.json"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

DBT_DIR = "/opt/airflow/dbt"
SQL_DIR = Path(__file__).resolve().parent / "sql"

def slack_alert(context):
    if not SLACK_WEBHOOK_URL:
        return

    task = context.get("task_instance")
    dag_id = context.get("dag").dag_id
    log_url = task.log_url

    message = (
        f":red_circle: *DAG 실패 알림*\n"
        f"• *DAG*: `{dag_id}`\n"
        f"• *Task*: `{task.task_id}`\n"
        f"• *실행 시각*: {context.get('execution_date')}\n"
        f"• *로그*: <{log_url}|여기 클릭>"
    )
    requests.post(SLACK_WEBHOOK_URL, json={"text": message}, timeout=10)


default_args = {
    "owner": "airflow",
    "start_date": datetime(2024, 1, 1),
    "retries": 1,
    "on_failure_callback": slack_alert,
}

with DAG(
    dag_id="clickstream_pipeline",
    default_args=default_args,
    schedule=None,
    catchup=False,
    tags=["clickstream", "bigquery", "dbt"],
    description="BigQuery DDL → dbt 모델링",
) as dag:
    # 1. BigQuery DDL 실행 (external/partitioned/clustered 테이블 생성)
    def create_bigquery_tables() -> None:
        from google.cloud import bigquery

        client = bigquery.Client.from_service_account_json(
            GCP_CREDS_PATH,
            project=GCP_PROJECT_ID,
        )

        sql_files = [
            SQL_DIR / "create_external_table.sql",
            SQL_DIR / "create_partitioned_table.sql",
            SQL_DIR / "create_partitioned_clustered_table.sql",
        ]

        for sql_file in sql_files:
            sql_template = sql_file.read_text(encoding="utf-8")
            query = sql_template.format(
                project_id=GCP_PROJECT_ID,
                dataset=BQ_DATASET,
                bucket=GCP_BUCKET,
            )
            client.query(query).result()

    create_bq_tables = PythonOperator(
        task_id="create_bigquery_tables",
        python_callable=create_bigquery_tables,
    )

    # 2. dbt 모델 실행 (stg → fct → mart)
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir . --target-path /tmp/dbt-target --log-path /tmp/dbt-logs",
    )

    # 3. dbt 데이터 품질 테스트
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir . --target-path /tmp/dbt-target --log-path /tmp/dbt-logs",
    )

    # 의존성
    (
        create_bq_tables
        >> dbt_run
        >> dbt_test
    )
