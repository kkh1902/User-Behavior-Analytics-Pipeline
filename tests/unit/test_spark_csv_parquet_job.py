from __future__ import annotations

import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col

from spark.jobs.csv_parquet_job import (
    add_partition_columns,
    bronze_schema,
    build_processed_df,
    cast_bronze_df,
    cast_fail_filter_expr,
    enforce_processed_schema,
    label_cast_failures,
)

pytestmark = pytest.mark.unit


@pytest.fixture(scope="session")
def spark() -> SparkSession:
    spark_session = (
        SparkSession.builder.master("local[1]")
        .appName("spark-csv-parquet-job-test")
        .getOrCreate()
    )
    spark_session.conf.set("spark.sql.session.timeZone", "UTC")
    yield spark_session
    spark_session.stop()


def test_cast_failures_are_detected_and_labeled(spark: SparkSession) -> None:
    # 문자열 숫자 캐스팅 실패 행은 failure_reason에 실패 컬럼명이 기록돼야 한다.
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
            "event_time": "2019-10-01 01:00:00 UTC",
            "event_type": "cart",
            "product_id": "bad_product",
            "category_id": "bad_category",
            "category_code": "electronics.smartphone",
            "brand": "samsung",
            "price": "bad_price",
            "user_id": "bad_user",
            "user_session": "s2",
        },
    ]
    df = spark.createDataFrame(rows, schema=bronze_schema())
    typed_df = cast_bronze_df(df)

    failed = typed_df.filter(cast_fail_filter_expr())
    labeled = label_cast_failures(failed).select("failure_reason").collect()

    assert len(labeled) == 1
    reason = labeled[0]["failure_reason"]
    assert "product_id" in reason
    assert "category_id" in reason
    assert "price" in reason
    assert "user_id" in reason


def test_processed_dataset_keeps_only_valid_rows_and_types(spark: SparkSession) -> None:
    # 핵심 식별 컬럼(event_time/user_id/product_id) 중 하나라도 invalid면 제외되어야 한다.
    rows = [
        {
            "event_time": "2019-11-01 00:00:00 UTC",
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
            "event_time": "bad_time",
            "event_type": "purchase",
            "product_id": "1002",
            "category_id": "2002",
            "category_code": "electronics.smartphone",
            "brand": "apple",
            "price": "199.5",
            "user_id": "3002",
            "user_session": "s2",
        },
    ]
    df = spark.createDataFrame(rows, schema=bronze_schema())
    processed = enforce_processed_schema(build_processed_df(cast_bronze_df(df)))

    assert processed.count() == 1
    record = processed.collect()[0]
    assert record["event_type"] == "view"
    assert record["product_id"] == 1001
    assert record["user_id"] == 3001

    assert dict(processed.dtypes)["event_time"] == "timestamp"
    assert dict(processed.dtypes)["product_id"] in {"bigint", "long"}
    assert dict(processed.dtypes)["price"] == "double"


def test_partition_columns_are_derived_from_event_time(spark: SparkSession) -> None:
    # partition 컬럼(event_month/event_date/event_month_date)이 UTC event_time 기준으로 파생돼야 한다.
    rows = [
        {
            "event_time": "2019-10-31 23:59:59 UTC",
            "event_type": "view",
            "product_id": "1001",
            "category_id": "2001",
            "category_code": "electronics.smartphone",
            "brand": "apple",
            "price": "10.0",
            "user_id": "3001",
            "user_session": "s1",
        }
    ]
    df = spark.createDataFrame(rows, schema=bronze_schema())
    processed = enforce_processed_schema(build_processed_df(cast_bronze_df(df)))
    with_partitions = add_partition_columns(processed)

    row = with_partitions.select(
        col("event_month"),
        col("event_date").cast("string").alias("event_date"),
        col("event_month_date").cast("string").alias("event_month_date"),
    ).collect()[0]

    assert row["event_month"] == "2019-10"
    assert row["event_date"] == "2019-10-31"
    assert row["event_month_date"] == "2019-10-01"
