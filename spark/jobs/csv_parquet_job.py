#!/usr/bin/env python3
import argparse
import logging

from pyspark.sql import SparkSession, types
from pyspark.sql.dataframe import DataFrame
from pyspark.sql.functions import (
    array,
    col,
    concat_ws,
    date_format,
    expr,
    lit,
    regexp_replace,
    to_date,
    to_timestamp,
    when,
)

# Job overview
# 1) Read the raw CSV using the Bronze (string) schema.
# 2) Cast key column types and count/reason cast failures.
# 3) Keep only valid rows, enforce the Processed schema for stable column types.
# 4) Derive event_date / event_month / event_month_date columns.
# 5) Write Parquet (Snappy) to GCS; optionally write invalid rows separately.
logger = logging.getLogger(__name__)


def configure_logging() -> None:
    # Configure the root logger to emit INFO and above to stdout
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    # Define runtime parameters
    # e.g. --bucket my-bucket --month 10
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
    # Build a SparkSession with GCS connector and service-account authentication
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


def bronze_schema() -> types.StructType:
    return types.StructType(
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


def processed_schema() -> types.StructType:
    return types.StructType(
        [
            types.StructField("event_time", types.TimestampType(), True),
            types.StructField("event_type", types.StringType(), True),
            types.StructField("product_id", types.LongType(), True),
            types.StructField("category_id", types.LongType(), True),
            types.StructField("category_code", types.StringType(), True),
            types.StructField("brand", types.StringType(), True),
            types.StructField("price", types.DoubleType(), True),
            types.StructField("user_id", types.LongType(), True),
            types.StructField("user_session", types.StringType(), True),
        ]
    )


def cast_bronze_df(df_bronze: DataFrame) -> DataFrame:
    return (
        df_bronze
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
    )


def cast_fail_filter_expr():
    # A row is considered a cast failure when the raw value is present but the typed value is NULL.
    return (
        (col("event_time_raw").isNotNull() & col("event_time_typed").isNull())
        | (col("product_id_raw").isNotNull() & col("product_id_typed").isNull())
        | (col("category_id_raw").isNotNull() & col("category_id_typed").isNull())
        | (col("price_raw").isNotNull() & col("price_typed").isNull())
        | (col("user_id_raw").isNotNull() & col("user_id_typed").isNull())
    )


def label_cast_failures(df_cast_fail: DataFrame) -> DataFrame:
    return df_cast_fail.withColumn(
        "failure_reason",
        concat_ws(
            ", ",
            array(
                when(
                    col("event_time_raw").isNotNull() & col("event_time_typed").isNull(),
                    lit("event_time"),
                ).otherwise(lit(None)),
                when(
                    col("product_id_raw").isNotNull() & col("product_id_typed").isNull(),
                    lit("product_id"),
                ).otherwise(lit(None)),
                when(
                    col("category_id_raw").isNotNull()
                    & col("category_id_typed").isNull(),
                    lit("category_id"),
                ).otherwise(lit(None)),
                when(
                    col("price_raw").isNotNull() & col("price_typed").isNull(),
                    lit("price"),
                ).otherwise(lit(None)),
                when(
                    col("user_id_raw").isNotNull() & col("user_id_typed").isNull(),
                    lit("user_id"),
                ).otherwise(lit(None)),
            ),
        ),
    )


def build_processed_df(df_bronze_typed: DataFrame) -> DataFrame:
    return (
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
    )


def enforce_processed_schema(df_processed: DataFrame) -> DataFrame:
    fixed_schema = processed_schema()
    return df_processed.select(
        *[
            col(field.name).cast(field.dataType).alias(field.name)
            for field in fixed_schema.fields
        ]
    )


def add_partition_columns(df_processed: DataFrame) -> DataFrame:
    return (
        df_processed.withColumn("event_date", to_date(col("event_time")))
        .withColumn("event_month", date_format(col("event_time"), "yyyy-MM"))
        .withColumn("event_month_date", expr("to_date(date_trunc('month', event_time))"))
    )


def main() -> None:
    # 1) Initialize logging, args, and Spark
    configure_logging()
    args = parse_args()
    spark = build_spark(args.app_name, args.gcs_keyfile)
    # Suppress Spark internal logs below WARN for cleaner application output
    spark.sparkContext.setLogLevel("WARN")
    # Pin session timezone to UTC since source event_time is UTC
    spark.conf.set("spark.sql.session.timeZone", "UTC")

    # 2) Compute target month and I/O paths
    month_map = {"10": "Oct", "11": "Nov"}
    month_name = month_map[args.month]
    input_path = f"gs://{args.bucket}/{args.raw_prefix}/2019-{month_name}.csv"
    output_processed = f"gs://{args.bucket}/{args.processed_prefix}"
    output_invalid = f"gs://{args.bucket}/{args.invalid_prefix}" if args.invalid_prefix else ""

    # Only replace the target partition on overwrite, leaving other partitions intact
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    # Bronze: all columns as strings to read raw CSV without data loss
    raw_schema = bronze_schema()

    # Processed: explicitly fixed schema used for analysis and loading
    fixed_schema = processed_schema()

    logger.info("Reading CSV: %s", input_path)
    # 3) Bronze load: read CSV with string schema to minimise raw data loss
    df_bronze = (
        spark.read.option("header", "true")
        .schema(raw_schema)
        .csv(input_path)
    )

    total_records = df_bronze.count()
    logger.info("Read complete: %s records", f"{total_records:,}")

    logger.info("Casting types...")
    # 4) Type casting + preserve original columns
    # *_raw:   original string value
    # *_typed: cast result
    df_bronze_typed = cast_bronze_df(df_bronze).cache()

    df_cast_fail = df_bronze_typed.filter(cast_fail_filter_expr())

    cast_fail_count = df_cast_fail.count()
    cast_fail_rate = cast_fail_count / total_records if total_records > 0 else 0.0
    logger.info("Cast failures: %s (%.4f%%)", f"{cast_fail_count:,}", cast_fail_rate * 100)

    if output_invalid and cast_fail_count > 0:
        logger.info("Writing invalid rows...")
        # Build comma-separated string of failed column names
        df_cast_fail_labeled = label_cast_failures(df_cast_fail)

        (
            # Save only raw columns needed for analysis plus failure_reason
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

    logger.info("Building processed dataset...")
    # Align column names and types explicitly to the Processed schema
    # Only rows with valid key identifiers (event_time/user_id/product_id) are kept
    df_processed = build_processed_df(df_bronze_typed).cache()

    # Release the intermediate cache once cast validation is done
    df_bronze_typed.unpersist()

    # Re-enforce the declared processed_schema to guard against schema drift
    df_processed = enforce_processed_schema(df_processed).select(*[col(field.name) for field in fixed_schema.fields])

    processed_count = df_processed.count()
    processed_rate = processed_count / total_records if total_records > 0 else 0.0
    logger.info("Processed records: %s (%.2f%%)", f"{processed_count:,}", processed_rate * 100)

    # Derive date columns for partitioning and aggregation
    df_processed_partitioned = add_partition_columns(df_processed)

    # Delete the target month partition before appending to prevent duplicate loads on re-run
    month_key = f"2019-{args.month}"
    partition_path = f"{output_processed}/event_month={month_key}"
    logger.info("Deleting target month partition if exists: %s", partition_path)
    hadoop_conf = spark._jsc.hadoopConfiguration()
    partition_fs_path = spark._jvm.org.apache.hadoop.fs.Path(partition_path)
    # Use the FileSystem instance matching the path scheme (gs://) to avoid Wrong FS errors.
    fs = partition_fs_path.getFileSystem(hadoop_conf)
    if fs.exists(partition_fs_path):
        fs.delete(partition_fs_path, True)

    logger.info("Writing processed parquet (append): %s", output_processed)
    (
        # Partition by event_month/event_date and compress with Snappy
        df_processed_partitioned.write.mode("append")
        .partitionBy("event_month", "event_date")
        .option("compression", "snappy")
        .parquet(output_processed)
    )

    # Release cache after write completes
    df_processed.unpersist()

    logger.info("Done")
    # 5) Clean up Spark resources
    spark.stop()


if __name__ == "__main__":
    main()
