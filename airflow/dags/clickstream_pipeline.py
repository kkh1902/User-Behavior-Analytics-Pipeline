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
        f":red_circle: *DAG Failure Alert*\n"
        f"• *DAG*: `{dag_id}`\n"
        f"• *Task*: `{task.task_id}`\n"
        f"• *Execution time*: {context.get('execution_date')}\n"
        f"• *Logs*: <{log_url}|Click here>"
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
    description="BigQuery DDL → dbt modelling",
) as dag:
    # 1. Run BigQuery DDL (create external / partitioned / clustered tables)
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

    # 2. Run dbt models (stg → fct → mart)
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && dbt run --profiles-dir . --target-path /tmp/dbt-target --log-path /tmp/dbt-logs",
    )

    # 3. Run dbt data quality tests
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && dbt test --profiles-dir . --target-path /tmp/dbt-target --log-path /tmp/dbt-logs",
    )

    # Dependencies
    (
        create_bq_tables
        >> dbt_run
        >> dbt_test
    )
