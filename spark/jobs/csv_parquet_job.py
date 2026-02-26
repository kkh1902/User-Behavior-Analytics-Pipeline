#!/usr/bin/env python3
import argparse
import logging

from pyspark.sql import SparkSession, types
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

# 잡 개요
# 1) 원본 CSV를 Bronze(string) 스키마로 읽는다.
# 2) 주요 컬럼 타입 캐스팅 + 캐스팅 실패 건수/사유를 산출한다.
# 3) 유효 행만 Processed 스키마로 정렬해 안정적인 컬럼 타입을 보장한다.
# 4) event_date / event_month / event_month_date 컬럼을 생성한다.
# 5) Parquet(Snappy)로 GCS에 저장하고, 필요 시 invalid 데이터를 분리 저장한다.
logger = logging.getLogger(__name__)


def configure_logging() -> None:
    # 표준 출력으로 INFO 이상 로그를 남기도록 기본 로거 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


def parse_args() -> argparse.Namespace:
    # 실행 시 전달받는 파라미터 정의
    # 예) --bucket my-bucket --month 10
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
    # GCS 커넥터 + 서비스계정 인증을 포함한 SparkSession 생성
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
    # 1) 로깅/인자/스파크 초기화
    configure_logging()
    args = parse_args()
    spark = build_spark(args.app_name, args.gcs_keyfile)
    # Spark 내부 로그는 WARN 이상만 표시(애플리케이션 로그 가독성 확보)
    spark.sparkContext.setLogLevel("WARN")
    # 원본 event_time이 UTC 기준이므로 세션 타임존을 UTC로 고정
    spark.conf.set("spark.sql.session.timeZone", "UTC")

    # 2) 실행 대상 월/입출력 경로 계산
    month_map = {"10": "Oct", "11": "Nov"}
    month_name = month_map[args.month]
    input_path = f"gs://{args.bucket}/{args.raw_prefix}/2019-{month_name}.csv"
    output_processed = f"gs://{args.bucket}/{args.processed_prefix}"
    output_invalid = f"gs://{args.bucket}/{args.invalid_prefix}" if args.invalid_prefix else ""

    # 파티션 overwrite 시 대상 파티션만 교체되도록 설정
    spark.conf.set("spark.sql.sources.partitionOverwriteMode", "dynamic")

    # Bronze: 원본 CSV를 손실 없이 읽기 위해 전 컬럼을 문자열로 정의
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

    # Processed: 분석/적재에 사용할 정제 스키마를 명시적으로 고정
    processed_schema = types.StructType(
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

    logger.info("Reading CSV: %s", input_path)
    # 3) Bronze 로딩: 문자열 스키마로 CSV를 읽어 원본 손실 최소화
    df_bronze = (
        spark.read.option("header", "true")
        .schema(bronze_schema)
        .csv(input_path)
    )

    total_records = df_bronze.count()
    logger.info("Read complete: %,d records", total_records)

    logger.info("Casting types...")
    # 4) 타입 캐스팅 + 원본 컬럼 보관
    # *_raw: 원본 문자열
    # *_typed: 캐스팅 결과
    df_bronze_typed = (
        df_bronze
        .withColumn("event_time_raw", col("event_time"))
        .withColumn(
            "event_time_typed",
            # " UTC" 접미어 제거 후 timestamp 파싱
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
        # 원본값은 있는데 typed 값이 NULL이면 캐스팅 실패로 간주
        (col("event_time_raw").isNotNull() & col("event_time_typed").isNull())
        | (col("product_id_raw").isNotNull() & col("product_id_typed").isNull())
        | (col("category_id_raw").isNotNull() & col("category_id_typed").isNull())
        | (col("price_raw").isNotNull() & col("price_typed").isNull())
        | (col("user_id_raw").isNotNull() & col("user_id_typed").isNull())
    )

    cast_fail_count = df_cast_fail.count()
    cast_fail_rate = cast_fail_count / total_records if total_records > 0 else 0.0
    logger.info("Cast failures: %,d (%.4f%%)", cast_fail_count, cast_fail_rate * 100)

    if output_invalid and cast_fail_count > 0:
        logger.info("Writing invalid rows...")
        # 실패 컬럼명을 쉼표 구분 문자열로 구성
        df_cast_fail_labeled = df_cast_fail.withColumn(
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

        (
            # 분석에 필요한 원본 컬럼 + failure_reason만 별도 저장
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
    # Processed 스키마에 맞게 컬럼명/타입을 명시적으로 정렬
    df_processed = (
        # 핵심 식별 컬럼(event_time/user_id/product_id)이 유효한 행만 채택
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

    # 캐스팅 검증이 끝난 중간 캐시는 메모리 반환
    df_bronze_typed.unpersist()

    # 스키마 드리프트 방지를 위해 선언한 processed_schema를 다시 한번 강제 적용
    df_processed = df_processed.select(
        *[
            # 선언 스키마 기준으로 타입/순서를 고정
            col(field.name).cast(field.dataType).alias(field.name)
            for field in processed_schema.fields
        ]
    )

    processed_count = df_processed.count()
    processed_rate = processed_count / total_records if total_records > 0 else 0.0
    logger.info("Processed records: %,d (%.2f%%)", processed_count, processed_rate * 100)

    # 파티션/집계용 날짜 컬럼 생성
    df_processed_partitioned = (
        # 일 단위 파티션 컬럼
        df_processed.withColumn("event_date", to_date(col("event_time")))
        # 월 라벨(문자열): 파티션 디렉터리 키로 사용
        .withColumn("event_month", date_format(col("event_time"), "yyyy-MM"))
        # 월 시작일(날짜형): BI 도구의 날짜 필터/정렬용
        .withColumn("event_month_date", expr("to_date(date_trunc('month', event_time))"))
    )

    # 재실행 시 중복 적재를 막기 위해 대상 월 파티션만 삭제 후 append 적재
    month_key = f"2019-{args.month}"
    partition_path = f"{output_processed}/event_month={month_key}"
    logger.info("Deleting target month partition if exists: %s", partition_path)
    hadoop_conf = spark._jsc.hadoopConfiguration()
    fs = spark._jvm.org.apache.hadoop.fs.FileSystem.get(hadoop_conf)
    partition_fs_path = spark._jvm.org.apache.hadoop.fs.Path(partition_path)
    if fs.exists(partition_fs_path):
        fs.delete(partition_fs_path, True)

    logger.info("Writing processed parquet (append): %s", output_processed)
    (
        # event_month/event_date 기준 파티셔닝 + snappy 압축 저장
        df_processed_partitioned.write.mode("append")
        .partitionBy("event_month", "event_date")
        .option("compression", "snappy")
        .parquet(output_processed)
    )

    # 저장 완료 후 캐시 해제
    df_processed.unpersist()

    logger.info("Done")
    # 5) Spark 리소스 정리
    spark.stop()


if __name__ == "__main__":
    main()
