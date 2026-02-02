-- 분석 테이블 (BigQuery)
-- 1) source_table은 clickstream_partitioned_clustered를 사용하세요.

-- datetime별 event_type 집계 테이블 (도넛/라인 차트 공용)
CREATE OR REPLACE TABLE `clickstream-pipeline-484705.clickstream.event_type_by_hour` AS
SELECT
  TIMESTAMP_TRUNC(event_time, HOUR) AS event_hour,
  event_type,
  COUNT(*) AS event_count
FROM `clickstream-pipeline-484705.clickstream.clickstream_partitioned_clustered`
GROUP BY event_hour, event_type;
