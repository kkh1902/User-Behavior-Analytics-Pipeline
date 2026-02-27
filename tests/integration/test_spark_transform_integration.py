from __future__ import annotations

import pytest
from pyspark.sql import SparkSession

from spark.jobs.csv_parquet_job import (
    add_partition_columns,
    bronze_schema,
    build_processed_df,
    cast_bronze_df,
    enforce_processed_schema,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    spark_session = SparkSession.builder.master("local[1]").appName("spark-integration-test").getOrCreate()
    spark_session.conf.set("spark.sql.session.timeZone", "UTC")
    yield spark_session
    spark_session.stop()


def test_sample_pipeline_flow_end_to_end(spark: SparkSession) -> None:
    # 샘플 입력 기준으로 cast -> processed -> partition 컬럼 생성까지 한 흐름으로 검증한다.
    rows = [
        {
            "event_time": "2019-10-01 00:00:00 UTC",
            "event_type": "view",
            "product_id": "1001",
            "category_id": "2001",
            "category_code": "electronics.smartphone",
            "brand": "apple",
            "price": "999.9",
            "user_id": "3001",
            "user_session": "s1",
        },
        {
            "event_time": "2019-10-01 00:01:00 UTC",
            "event_type": "cart",
            "product_id": "1001",
            "category_id": "2001",
            "category_code": "electronics.smartphone",
            "brand": "apple",
            "price": "999.9",
            "user_id": "3001",
            "user_session": "s1",
        },
    ]
    bronze = spark.createDataFrame(rows, schema=bronze_schema())
    typed = cast_bronze_df(bronze)
    processed = enforce_processed_schema(build_processed_df(typed))
    partitioned = add_partition_columns(processed)

    assert partitioned.count() == 2
    assert set(partitioned.columns) >= {"event_month", "event_date", "event_month_date"}
