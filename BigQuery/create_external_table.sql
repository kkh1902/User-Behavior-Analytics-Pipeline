-- BigQuery External Table (GCS Parquet)
-- 1) Bucket is based on clickstream-pipeline-484705-clickstream-data.
-- 2) Spark output path example: gs://<bucket>/processed/clickstream/2019-Oct/ ...
-- 3) Hive partitioning auto-detects partition columns (event_month, event_date).

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
