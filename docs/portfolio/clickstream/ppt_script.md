# Clickstream Pipeline Presentation Script (16-Slide Detailed Version)

## Slide 1. Title
Hello. This presentation covers my experience building a data pipeline that analyses conversion funnel bottlenecks using clickstream data. The key achievement is connecting every step — from ingestion to a BI dashboard — into a single operable flow.

## Slide 2. Business Problem Definition
The problem was not simply that conversion rates were low; there was no framework to explain why drop-off occurred. In practice, there were periods where traffic increased but purchases did not follow, and the variance across categories and brands was significant. I decomposed the funnel into `view → cart → purchase` and made it possible to compare which segments had the largest losses at each stage. I also split causal hypotheses into price/content issues versus payment/shipping UX issues to design an actionable analysis structure.

## Slide 3. Goals and KPIs
There are three goals: pipeline automation, KPI standardisation, and connecting analysis results to executable actions. The KPIs are fixed as `view_to_cart_rate`, `cart_to_purchase_rate`, and `overall_conversion_rate` to ensure consistent interpretation.

## Slide 4. Architecture
The architecture flows through: Kaggle ingestion, GCS storage, Spark transformation, BigQuery loading, dbt modelling, and Looker Studio visualisation. Separating the storage, processing, and analytics layers achieves both operability and scalability.

## Slide 5. Infrastructure Implementation
Infrastructure is codified with Terraform. Provisioning the GCS bucket and BigQuery dataset ensures environment reproducibility, reduces setup errors compared to manual configuration, and shortens initial build time.

## Slide 6. Airflow DAG Structure
Airflow is split into 3 DAGs by responsibility: ingest, transform, and modelling. Separating the stages allows fast identification of failure points and improves incident response speed during operations.

## Slide 7. Ingest DAG
`clickstream_ingest_raw` performs Kaggle download, unzip, and GCS upload. Automating these repetitive tasks standardises the source data ingestion process.

## Slide 8. Spark Transform DAG
`clickstream_spark_transform` uploads the Spark job file to GCS and then processes October and November data on Dataproc. Specifying Spark resource parameters ensures stable transformation execution.

## Slide 9. Core Spark Logic
The Spark job first reads with a Bronze string schema and then performs type casting. Cast failures are labelled with `failure_reason` to make them traceable. Valid data is enforced against the Processed schema to guarantee data type stability.

## Slide 10. Storage Strategy
Results are stored as Parquet (Snappy) and partitioned by `event_month` and `event_date`. On re-run the target month partition is deleted before appending, which reduces the risk of duplicate loading.

## Slide 11. BigQuery Implementation
BigQuery uses three SQL files to create an external table, a partitioned table, and a partitioned + clustered table. This structure provides both raw accessibility and analytical query performance.

## Slide 12. dbt Staging
`stg_clickstream` performs event-type filtering, null removal for key columns, and derives `category_main` from `category_code`. This step normalises raw logs into a standard analytical form.

## Slide 13. dbt Mart
`fct_funnel_events` creates per-session + per-product funnel reach flags, while `mart_funnel` and `mart_daily_funnel_kpi` provide BI-ready aggregations. As a result, monthly and daily conversion rates can be compared consistently using the same definition.

## Slide 14. Quality / Testing
Quality is validated through dbt tests and code tests. unit/integration tests are implemented; load/resilience/performance are managed as TODO. By separating implemented from not-yet-implemented scope, operational risk is managed transparently.

## Slide 15. Dashboard and Insights
Looker Studio shows conversion trends, category/brand comparisons, and stage distributions together. For example, if `view_to_cart_rate` is low, product detail pages or price competitiveness are the first suspects; if `cart_to_purchase_rate` is low, payment UX or shipping fee policies are checked first. Sharp drops on specific dates are cross-referenced with campaign quality, inventory, and operational incident logs for root-cause analysis. Insights are mapped directly to action items to set improvement priorities.

## Slide 16. Limitations and Improvement Plan
The current batch-centric design limits near-real-time response. Short-term: strengthen monitoring and testing. Medium-term: add segment/cohort/retention analysis models. Long-term: evaluate migration to a streaming ingestion and processing architecture.
