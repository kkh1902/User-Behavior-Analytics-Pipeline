from __future__ import annotations

import os
from datetime import datetime

import requests
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.google.cloud.operators.dataproc import DataprocSubmitJobOperator
from google.cloud import storage

GCP_BUCKET = os.environ.get("GCP_BUCKET_NAME", "clickstream-pipeline-484705-clickstream-data")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "clickstream-pipeline-484705")
GCP_CREDS_PATH = "/cred/clickstream-sa.json"
DATAPROC_REGION = os.environ.get("DATAPROC_REGION", "us-east5")
DATAPROC_CLUSTER_NAME = os.environ.get("DATAPROC_CLUSTER_NAME", "clickstream-dp")
LOCAL_SPARK_JOB = "/opt/airflow/spark/jobs/csv_parquet_job.py"
GCS_SPARK_JOB = f"gs://{GCP_BUCKET}/code/csv_parquet_job.py"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

_SPARK_PROPERTIES = {
    "spark.network.timeout": "300s",
    "spark.executor.heartbeatInterval": "60s",
    "spark.dynamicAllocation.enabled": "false",
    # Scale executor parallelism to utilise the 4-worker cluster
    "spark.executor.instances": "4",
    "spark.executor.cores": "2",
    "spark.executor.memory": "4g",
    "spark.driver.memory": "2g",
    "spark.sql.shuffle.partitions": "384",
}


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


def upload_spark_job_to_gcs() -> None:
    """Upload the PySpark job file to GCS so Dataproc can execute it."""
    client = storage.Client.from_service_account_json(GCP_CREDS_PATH, project=GCP_PROJECT_ID)
    bucket = client.bucket(GCP_BUCKET)
    blob = bucket.blob("code/csv_parquet_job.py")
    blob.upload_from_filename(LOCAL_SPARK_JOB)


with DAG(
    dag_id="clickstream_spark_transform",
    default_args=default_args,
    schedule=None,
    catchup=False,
    # Prevent multiple simultaneous Dataproc jobs from duplicate triggers
    max_active_runs=1,
    tags=["clickstream", "spark", "transform", "dataproc"],
    description="Dataproc Cluster Spark CSV -> Parquet transformation",
) as dag:
    upload_job = PythonOperator(
        task_id="upload_spark_job_to_gcs",
        python_callable=upload_spark_job_to_gcs,
    )

    spark_oct_job = {
        "reference": {"project_id": GCP_PROJECT_ID},
        "placement": {"cluster_name": DATAPROC_CLUSTER_NAME},
        "pyspark_job": {
            "main_python_file_uri": GCS_SPARK_JOB,
            "args": ["--bucket", GCP_BUCKET, "--month", "10"],
            "properties": _SPARK_PROPERTIES,
        },
    }

    spark_oct = DataprocSubmitJobOperator(
        task_id="spark_csv_to_parquet_oct",
        project_id=GCP_PROJECT_ID,
        region=DATAPROC_REGION,
        job=spark_oct_job,
        gcp_conn_id="google_cloud_default",
    )

    spark_nov_job = {
        "reference": {"project_id": GCP_PROJECT_ID},
        "placement": {"cluster_name": DATAPROC_CLUSTER_NAME},
        "pyspark_job": {
            "main_python_file_uri": GCS_SPARK_JOB,
            "args": ["--bucket", GCP_BUCKET, "--month", "11"],
            "properties": _SPARK_PROPERTIES,
        },
    }

    spark_nov = DataprocSubmitJobOperator(
        task_id="spark_csv_to_parquet_nov",
        project_id=GCP_PROJECT_ID,
        region=DATAPROC_REGION,
        job=spark_nov_job,
        gcp_conn_id="google_cloud_default",
    )

    # Run monthly jobs sequentially to reduce resource contention.
    upload_job >> spark_oct >> spark_nov
