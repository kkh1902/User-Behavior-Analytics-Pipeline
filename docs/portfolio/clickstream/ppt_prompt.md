# Clickstream Pipeline Portfolio PPT Generation Prompt (No Implementation Details Omitted)

Use the requirements below to create an English presentation PPT.
Key rule: **no implemented item may be left out.**

## 1) Presentation Conditions
- Purpose: data engineer portfolio interview presentation
- Duration: 7–10 minutes
- Slides: 10
- Structure: maintain the `Problem → Solution → Outcome` flow on every slide

## 2) Output Format (common to each slide)
- 1 title
- 4–6 key bullets
- 1 visual element suggestion
- 3–5 sentences of presenter notes

## 3) "Implemented" Checklist — Must Include
The items below must appear explicitly in a logical position in the slides, not just somewhere.

### A. Orchestration / Airflow
- List the names and roles of all 3 DAGs accurately:
  - `clickstream_ingest_raw`: Kaggle download → unzip → GCS upload
  - `clickstream_spark_transform`: upload Spark job, then run Dataproc jobs for Oct/Nov
  - `clickstream_pipeline`: BigQuery DDL → `dbt run` → `dbt test`
- Failure alerts: Slack webhook callback

### B. Spark Transformation
- File: `spark/jobs/csv_parquet_job.py`
- Key implementation:
  - Bronze string schema loading
  - Cast failure detection and `failure_reason` labelling
  - Filter valid rows, enforce Processed schema
  - Derive `event_month`, `event_date`, `event_month_date`
  - Write Parquet (Snappy)
  - Delete target month partition, then append

### C. BigQuery
- State that 3 SQL files are executed:
  - `create_external_table.sql`
  - `create_partitioned_table.sql`
  - `create_partitioned_clustered_table.sql`

### D. dbt Models
- State the names and roles of all 4 models accurately:
  - `stg_clickstream`
  - `fct_funnel_events`
  - `mart_funnel`
  - `mart_daily_funnel_kpi`
- Include all 3 conversion KPIs:
  - `view_to_cart_rate`
  - `cart_to_purchase_rate`
  - `overall_conversion_rate`

### E. Testing / Quality
- Implemented tests:
  - unit: DAG structure validation, Spark transform function validation
  - integration: Spark transform sample E2E
  - dbt test: `accepted_values`, `not_null`
- Honestly state what is NOT implemented:
  - load/resilience/performance tests are TODO (currently skipped)

### F. Infrastructure
- State that Terraform provisions the GCS bucket and BigQuery dataset

## 4) Per-Slide Requirements
1. Project overview
2. Problem definition / KPI
3. Architecture
4. Airflow 3-DAG implementation
5. Spark transformation logic
6. BigQuery DDL + loading strategy
7. dbt 4 models
8. Test / quality status (implemented vs TODO)
9. Looker Studio dashboard and insights
10. Limitations / improvement roadmap

## 5) Writing Rules
- Use exact file / model / DAG names
- Do not describe features that do not exist
- Do not invent numbers if they are not confirmed
- Writing style: factual and professional, no exaggeration
