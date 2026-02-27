CREATE OR REPLACE TABLE `{project_id}.{dataset}.clickstream_partitioned`
PARTITION BY event_date
AS
SELECT
  event_time,
  event_type,
  product_id,
  category_id,
  category_code,
  brand,
  price,
  user_id,
  user_session,
  event_month_date,
  event_date,
  event_month
FROM `{project_id}.{dataset}.clickstream_external`;
