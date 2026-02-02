-- BigQuery Native Tables (from external)
-- Prereq: run create_external_table.sql first to create the external table

-- 1) Partitioned only
CREATE OR REPLACE TABLE `clickstream-pipeline-484705.clickstream.clickstream_partitioned`
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
  event_date,
  event_month
FROM `clickstream-pipeline-484705.clickstream.clickstream_external`;
