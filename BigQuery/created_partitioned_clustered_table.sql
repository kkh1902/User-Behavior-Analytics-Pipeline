-- 2) Partitioned + Clustered
CREATE OR REPLACE TABLE `clickstream-pipeline-484705.clickstream.clickstream_partitioned_clustered`
PARTITION BY event_date
CLUSTER BY event_type
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