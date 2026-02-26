from __future__ import annotations

import glob
import os
from datetime import datetime

import requests
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator

GCP_BUCKET = os.environ.get("GCP_BUCKET_NAME", "clickstream-pipeline-484705-clickstream-data")
GCP_CREDS_PATH = "/cred/clickstream-sa.json"
SPARK_JOB = "/opt/airflow/spark/jobs/csv_parquet_job.py"
GCS_CONNECTOR_JAR = "/opt/gcs-jars/gcs-connector-hadoop3-shaded.jar"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

DBT_DIR = "/opt/airflow/dbt"

_SPARK_GCS_CONF = {
    "spark.hadoop.fs.gs.impl": "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem",
    "spark.hadoop.fs.AbstractFileSystem.gs.impl": "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS",
    "spark.hadoop.google.cloud.auth.service.account.enable": "true",
    "spark.hadoop.google.cloud.auth.service.account.json.keyfile": GCP_CREDS_PATH,
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
    "retries": 1,
    "on_failure_callback": slack_alert,
}

with DAG(
    dag_id="clickstream_pipeline",
    default_args=default_args,
    schedule=None,
    catchup=False,
    tags=["clickstream", "gcs", "spark", "dbt"],
    description="Kaggle CSV 다운로드 → GCS 업로드 → Spark 변환 → dbt 모델링",
) as dag:

    # 1. Kaggle 데이터셋 다운로드
    download_dataset = BashOperator(
        task_id="download_kaggle_dataset",
        bash_command=(
            "mkdir -p /tmp/clickstream_raw && "
            "cd /tmp/clickstream_raw && "
            "kaggle datasets download mkechinov/ecommerce-behavior-data-from-multi-category-store --force"
        ),
    )

    # 2. 다운로드된 압축 파일 해제
    unzip_dataset = BashOperator(
        task_id="unzip_dataset",
        bash_command=(
            "cd /tmp/clickstream_raw && "
            "unzip -o *.zip -d extracted && "
            "ls -lah extracted/"
        ),
    )

    # 3. CSV 파일을 GCS로 업로드
    def upload_csvs_to_gcs() -> None:
        from google.cloud import storage

        client = storage.Client.from_service_account_json(GCP_CREDS_PATH)
        bucket = client.bucket(GCP_BUCKET)

        csv_files = glob.glob("/tmp/clickstream_raw/extracted/*.csv")
        if not csv_files:
            raise FileNotFoundError("업로드할 CSV 파일이 없습니다: /tmp/clickstream_raw/extracted/")

        for local_path in csv_files:
            filename = os.path.basename(local_path)
            blob_name = f"raw/kaggle/{filename}"
            blob = bucket.blob(blob_name)
            blob.upload_from_filename(local_path)
            print(f"업로드 완료: {filename} → gs://{GCP_BUCKET}/{blob_name}")

    upload_to_gcs = PythonOperator(
        task_id="upload_csvs_to_gcs",
        python_callable=upload_csvs_to_gcs,
    )

    # 4. Spark: 10월 CSV → Parquet 변환
    spark_oct = SparkSubmitOperator(
        task_id="spark_csv_to_parquet_oct",
        conn_id="spark_default",
        application=SPARK_JOB,
        application_args=[
            "--bucket", GCP_BUCKET,
            "--month", "10",
            "--gcs-keyfile", GCP_CREDS_PATH,
        ],
        jars=GCS_CONNECTOR_JAR,
        conf=_SPARK_GCS_CONF,
        name="clickstream_csv_to_parquet_oct",
    )

    # 5. Spark: 11월 CSV → Parquet 변환
    spark_nov = SparkSubmitOperator(
        task_id="spark_csv_to_parquet_nov",
        conn_id="spark_default",
        application=SPARK_JOB,
        application_args=[
            "--bucket", GCP_BUCKET,
            "--month", "11",
            "--gcs-keyfile", GCP_CREDS_PATH,
        ],
        jars=GCS_CONNECTOR_JAR,
        conf=_SPARK_GCS_CONF,
        name="clickstream_csv_to_parquet_nov",
    )

    # 6. dbt 모델 실행 (stg → fct → mart)
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=f"cd {DBT_DIR} && .venv/bin/dbt run --profiles-dir .",
    )

    # 7. dbt 데이터 품질 테스트
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=f"cd {DBT_DIR} && .venv/bin/dbt test --profiles-dir .",
    )

    # 의존성
    download_dataset >> unzip_dataset >> upload_to_gcs >> [spark_oct, spark_nov] >> dbt_run >> dbt_test
