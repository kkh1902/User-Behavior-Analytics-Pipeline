-- BigQuery External Table (GCS Parquet)
-- 1) 버킷은 clickstream-pipeline-484705-clickstream-data 기준입니다.
-- 2) Spark 출력 경로가 예: gs://<bucket>/processed/clickstream/2019-Oct/ ...
-- 3) hive partitioning을 사용하므로 파티션 컬럼(event_month, event_date)을 자동 인식합니다.

CREATE OR REPLACE EXTERNAL TABLE `clickstream-pipeline-484705.clickstream.clickstream_external`
(
  event_time TIMESTAMP,
  event_type STRING,
  product_id INT64,
  category_id INT64,
  category_code STRING,
  brand STRING,
  price FLOAT64,
  user_id INT64,
  user_session STRING
)
WITH PARTITION COLUMNS (
  event_month STRING,
  event_date DATE
)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://clickstream-pipeline-484705-clickstream-data/processed/clickstream/*'],
  hive_partition_uri_prefix = 'gs://clickstream-pipeline-484705-clickstream-data/processed/clickstream/'
);
코드 