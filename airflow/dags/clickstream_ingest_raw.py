from __future__ import annotations

import glob
import os
import zipfile
from datetime import datetime

import requests
from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

GCP_BUCKET = os.environ.get("GCP_BUCKET_NAME", "clickstream-pipeline-484705-clickstream-data")
GCP_CREDS_PATH = "/cred/clickstream-sa.json"
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")


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
    dag_id="clickstream_ingest_raw",
    default_args=default_args,
    schedule=None,
    catchup=False,
    tags=["clickstream", "ingest", "kaggle", "gcs"],
    description="Kaggle CSV 다운로드 → 압축 해제 → GCS 업로드",
) as dag:
    download_dataset = BashOperator(
        task_id="download_kaggle_dataset",
        bash_command=(
            "mkdir -p /tmp/clickstream_raw && "
            "cd /tmp/clickstream_raw && "
            "kaggle datasets download mkechinov/ecommerce-behavior-data-from-multi-category-store --force"
        ),
    )

    def unzip_kaggle_archive() -> None:
        raw_dir = "/tmp/clickstream_raw"
        extracted_dir = os.path.join(raw_dir, "extracted")
        os.makedirs(extracted_dir, exist_ok=True)

        zip_files = glob.glob(os.path.join(raw_dir, "*.zip"))
        if not zip_files:
            raise FileNotFoundError("압축 파일이 없습니다: /tmp/clickstream_raw/*.zip")

        for zip_path in zip_files:
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(extracted_dir)

        print(f"압축 해제 완료: {extracted_dir}")

    unzip_dataset = PythonOperator(
        task_id="unzip_dataset",
        python_callable=unzip_kaggle_archive,
    )

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

    download_dataset >> unzip_dataset >> upload_to_gcs
