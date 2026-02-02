-- Analysis table (BigQuery)
-- 1) Use clickstream_partitioned_clustered as the source table.

-- Hourly event_type aggregation table (for donut/line charts)
CREATE OR REPLACE TABLE `clickstream-pipeline-484705.clickstream.event_type_by_hour` AS
SELECT
  TIMESTAMP_TRUNC(event_time, HOUR) AS event_hour,
  event_type,
  COUNT(*) AS event_count
FROM `clickstream-pipeline-484705.clickstream.clickstream_partitioned_clustered`
GROUP BY event_hour, event_type;
