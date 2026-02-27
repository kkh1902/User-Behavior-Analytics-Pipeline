CREATE OR REPLACE EXTERNAL TABLE `{project_id}.{dataset}.clickstream_external`
(
  event_time TIMESTAMP,
  event_type STRING,
  product_id INT64,
  category_id INT64,
  category_code STRING,
  brand STRING,
  price FLOAT64,
  user_id INT64,
  user_session STRING,
  event_month_date DATE
)
WITH PARTITION COLUMNS (
  event_month STRING,
  event_date DATE
)
OPTIONS (
  format = 'PARQUET',
  uris = ['gs://{bucket}/processed/clickstream/*'],
  hive_partition_uri_prefix = 'gs://{bucket}/processed/clickstream/'
);
