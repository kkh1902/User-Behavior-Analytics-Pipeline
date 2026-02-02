#!/usr/bin/env python3
import argparse

from pyspark.sql import SparkSession, types
from pyspark.sql.functions import (
    array,
    col,
    concat_ws,
    date_format,
    lit,
    monotonically_increasing_id,
    regexp_replace,
    to_date,
    to_timestamp,
    when,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CSV to Parquet (GCS) job")
    parser.add_argument("--bucket", required=True, help="GCS bucket name")
    parser.add_argument("--month", required=True, choices=["10", "11"], help="Month (10 or 11)")
    parser.add_argument("--raw-prefix", default="raw/kaggle", help="GCS raw prefix")
    parser.add_argument("--processed-prefix", default="processed/clickstream", help="GCS processed prefix")
    parser.add_argument("--invalid-prefix", default="", help="GCS invalid prefix (optional)")
    parser.add_argument(
        "--gcs-keyfile",
        default="/cred/clickstream-sa.json",
        help="Service account JSON path inside Spark containers",
    )
    parser.add_argument("--app-name", default="csv_parquet_job", help="Spark app name")
    return parser.parse_args()


def build_spark(app_name: str, gcs_keyfile: str) -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        .config("spark.hadoop.fs.gs.impl", "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFileSystem")
        .config(
            "spark.hadoop.fs.AbstractFileSystem.gs.impl",
            "com.google.cloud.hadoop.fs.gcs.GoogleHadoopFS",
        )
        .config("spark.hadoop.google.cloud.auth.service.account.enable", "true")
        .config("spark.hadoop.google.cloud.auth.service.account.json.keyfile", gcs_keyfile)
        .getOrCreate()
    )


def main() -> None:
    args = parse_args()
    spark = build_spark(args.app_name, args.gcs_keyfile)
    spark.sparkContext.setLogLevel("WARN")

    month_map = {"10": "Oct", "11": "Nov"}
    month_name = month_map[args.month]
    input_path = f"gs://{args.bucket}/{args.raw_prefix}/2019-{month_name}.csv"
    output_silver = f"gs://{args.bucket}/{args.processed_prefix}"
    output_invalid = f"gs://{args.bucket}/{args.invalid_prefix}" if args.invalid_prefix else ""

    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    bronze_schema = types.StructType(
        [
            types.StructField("event_time", types.StringType(), True),
            types.StructField("event_type", types.StringType(), True),
            types.StructField("product_id", types.StringType(), True),
            types.StructField("category_id", types.StringType(), True),
            types.StructField("category_code", types.StringType(), True),
            types.StructField("brand", types.StringType(), True),
            types.StructField("price", types.StringType(), True),
            types.StructField("user_id", types.StringType(), True),
            types.StructField("user_session", types.StringType(), True),
        ]
    )

    print(f"Reading CSV: {input_path}")
    df_bronze = (
        spark.read.option("header", "true")
        .schema(bronze_schema)
        .csv(input_path)
    )

    total_records = df_bronze.count()
    print(f"Read complete: {total_records:,} records")

    print("Casting types...")
    df_bronze_typed = (
        df_bronze.withColumn("_row_id", monotonically_increasing_id())
        .withColumn("event_time_raw", col("event_time"))
        .withColumn(
            "event_time_typed",
            to_timestamp(regexp_replace(col("event_time"), " UTC$", ""), "yyyy-MM-dd HH:mm:ss"),
        )
        .withColumn("product_id_raw", col("product_id"))
        .withColumn("product_id_typed", col("product_id").cast("long"))
        .withColumn("category_id_raw", col("category_id"))
        .withColumn("category_id_typed", col("category_id").cast("long"))
        .withColumn("price_raw", col("price"))
        .withColumn("price_typed", col("price").cast("double"))
        .withColumn("user_id_raw", col("user_id"))
        .withColumn("user_id_typed", col("user_id").cast("long"))
    ).cache()

    df_cast_fail = df_bronze_typed.filter(
        (col("event_time_raw").isNotNull() & col("event_time_typed").isNull())
        | (col("product_id_raw").isNotNull() & col("product_id_typed").isNull())
        | (col("category_id_raw").isNotNull() & col("category_id_typed").isNull())
        | (col("price_raw").isNotNull() & col("price_typed").isNull())
        | (col("user_id_raw").isNotNull() & col("user_id_typed").isNull())
    )

    cast_fail_count = df_cast_fail.count()
    cast_fail_rate = cast_fail_count / total_records if total_records > 0 else 0.0
    print(f"Cast failures: {cast_fail_count:,} ({cast_fail_rate:.4%})")

    if output_invalid and cast_fail_count > 0:
        print("Writing invalid rows...")
        df_cast_fail_labeled = df_cast_fail.withColumn(
            "failure_reason",
            concat_ws(
                ", ",
                array(
                    when(
                        col("event_time_raw").isNotNull() & col("event_time_typed").isNull(),
                        lit("event_time"),
                    ).otherwise(lit("")),
                    when(
                        col("product_id_raw").isNotNull() & col("product_id_typed").isNull(),
                        lit("product_id"),
                    ).otherwise(lit("")),
                    when(
                        col("category_id_raw").isNotNull()
                        & col("category_id_typed").isNull(),
                        lit("category_id"),
                    ).otherwise(lit("")),
                    when(
                        col("price_raw").isNotNull() & col("price_typed").isNull(),
                        lit("price"),
                    ).otherwise(lit("")),
                    when(
                        col("user_id_raw").isNotNull() & col("user_id_typed").isNull(),
                        lit("user_id"),
                    ).otherwise(lit("")),
                ),
            ),
        )

        (
            df_cast_fail_labeled.select(
                "event_time_raw",
                "event_type",
                "product_id_raw",
                "category_id_raw",
                "category_code",
                "brand",
                "price_raw",
                "user_id_raw",
                "user_session",
                "failure_reason",
            )
            .write.mode("overwrite")
            .parquet(output_invalid)
        )

    print("Building silver dataset...")
    df_silver = (
        df_bronze_typed.filter(
            col("event_time_typed").isNotNull()
            & col("user_id_typed").isNotNull()
            & col("product_id_typed").isNotNull()
        )
        .select(
            col("event_time_typed").alias("event_time"),
            col("event_type"),
            col("product_id_typed").alias("product_id"),
            col("category_id_typed").alias("category_id"),
            col("category_code"),
            col("brand"),
            col("price_typed").alias("price"),
            col("user_id_typed").alias("user_id"),
            col("user_session"),
        )
        .cache()
    )

    silver_count = df_silver.count()
    silver_rate = silver_count / total_records if total_records > 0 else 0.0
    print(f"Silver records: {silver_count:,} ({silver_rate:.2%})")

    df_silver_partitioned = (
        df_silver.withColumn("event_date", to_date(col("event_time")))
        .withColumn("event_month", date_format(col("event_time"), "yyyy-MM"))
    )

    print(f"Writing silver parquet: {output_silver}")
    (
        df_silver_partitioned.write.mode("overwrite")
        .partitionBy("event_month", "event_date")
        .option("compression", "snappy")
        .parquet(output_silver)
    )

    print("Done")
    spark.stop()


if __name__ == "__main__":
    main()
