# Spark Processing

## Notebook
`com_csv_parquet.ipynb` reads raw clickstream CSVs from GCS, validates/casts types, and writes partitioned Parquet back to GCS.

### What it does
1. Create a Spark session with the GCS connector and service account auth.
2. Load GCS CSVs using a bronze (all-string) schema.
3. Set input/output paths and confirm load results.
4. Cast key columns (`event_time`, `product_id`, `category_id`, `price`, `user_id`).
5. Count cast failures and label failure reasons.
6. If failures exist, write them to `raw/invalid` as Parquet.
7. Build the processed dataset from valid rows only.
8. Add `event_month` and `event_date` partition columns.
9. Write Snappy-compressed Parquet to `processed/clickstream`.

### Key column conversions
- `event_time`: `string` → `timestamp` (`yyyy-MM-dd HH:mm:ss`, strips trailing ` UTC`)
- `product_id`: `string` → `long`
- `category_id`: `string` → `long`
- `price`: `string` → `double`
- `user_id`: `string` → `long`

### Data validation
- Cast failures are checked per column.
- Failed rows include a `failure_reason` column.

### Input/Output
- Input: `gs://<bucket>/raw/2019-Oct.csv`, `gs://<bucket>/raw/2019-Nov.csv`
- Output (processed): `gs://<bucket>/processed/clickstream`
- Output (invalid): `gs://<bucket>/raw/invalid`

### Notes
- Update the GCS bucket name in the notebook if your project differs.
- Requires a valid service account key at `/cred/clickstream-sa.json`.

## Docker setup (requirements)
Below is the minimal configuration expected for running the notebook in a containerized Spark environment.

### Dockerfile expectations
- Base image with Java + Python + Spark + Jupyter (or install them).
- `pyspark` and required Python libs (e.g., `pandas`, `pyarrow`) installed.
- GCS connector JAR available on the Spark classpath.
- Working directory mounted to `/home/spark/work` (or similar).

### docker-compose expectations
- Services: `spark-master`, `spark-worker`, and `notebook` (optional but recommended).
- Expose:
  - Spark Master UI: `8080`
  - Spark Master port: `7077`
  - Notebook: `8888`
- Mounts:
  - Project workspace to the notebook container.
  - Service account key to `/cred/clickstream-sa.json`.
- Environment:
  - `SPARK_MASTER=spark://spark-master:7077`
  - `PYSPARK_PYTHON=python3`
