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
    # 4 worker 클러스터를 활용하도록 executor 병렬도를 확장
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
    # 비용 통제를 위해 실패 시 자동 재시도는 끔
    "retries": 0,
    "on_failure_callback": slack_alert,
}


def upload_spark_job_to_gcs() -> None:
    """Dataproc 클러스터에서 실행할 pyspark 파일을 GCS에 업로드합니다."""
    client = storage.Client.from_service_account_json(GCP_CREDS_PATH, project=GCP_PROJECT_ID)
    bucket = client.bucket(GCP_BUCKET)
    blob = bucket.blob("code/csv_parquet_job.py")
    blob.upload_from_filename(LOCAL_SPARK_JOB)


with DAG(
    dag_id="clickstream_spark_transform",
    default_args=default_args,
    schedule=None,
    catchup=False,
    # 중복 트리거로 여러 Dataproc 잡이 동시에 뜨지 않도록 제한
    max_active_runs=1,
    tags=["clickstream", "spark", "transform", "dataproc"],
    description="Dataproc Cluster Spark CSV -> Parquet 변환",
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

    # 월별 잡은 순차 실행으로 리소스 경합을 줄입니다.
    upload_job >> spark_oct >> spark_nov
