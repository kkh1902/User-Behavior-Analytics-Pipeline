# Clickstream Pipeline PPT Slide Detailed Outline (Expanded Presentation Version)

## Slide 1. Project Introduction
- Title: Building a Clickstream Conversion Funnel Analysis Pipeline
- One-liner: "Solving the problem of high traffic but low purchases with a data pipeline"
- Problem: Data was scattered, making it difficult to measure conversion bottlenecks consistently
- Solution: Implemented ingestion → transformation → loading → modelling → visualisation as a single operational flow
- Outcome: Established a foundation for periodically reviewing funnel KPIs and prioritising improvements
- Visual element: Pipeline icon timeline
- Presenter point: Emphasise first that this project connects a business problem to a technical implementation

## Slide 2. Problem Definition (Detail)
- Symptom 1: Sufficient view traffic, but purchase conversion is below expectations
- Symptom 2: Cases where purchases do not increase proportionally even as traffic grows
- Symptom 3: Large variance across categories/brands with no framework to explain causes
- Hypothesis A: Inadequate product info / price / reviews → `view → cart` drop-off
- Hypothesis B: Shipping cost / checkout complexity / trust issues → `cart → purchase` drop-off
- Data challenge: Raw log quality variance creates metric reliability risk
- Solution goal: Identify the loss stage and improvement targets with data
- Visual element: Funnel + causal hypothesis mapping diagram
- Presenter point: Reframe the problem from "conversion is low" to "where and why is it low"

## Slide 3. Goals and KPI Definition
- Goal 1: Automate the batch pipeline with no manual steps
- Goal 2: Standardise conversion KPI definitions (consistent team-wide metric interpretation)
- Goal 3: Connect analysis results to executable actions
- KPI 1: `view_to_cart_rate` = cart / view
- KPI 2: `cart_to_purchase_rate` = purchase / cart
- KPI 3: `overall_conversion_rate` = purchase / view
- Analysis axes: month/day, category, brand, session + product
- Visual element: KPI definition table
- Presenter point: Highlight that fixing KPIs first reduces future debate costs

## Slide 4. Overall Architecture
- Input: Kaggle E-commerce Behavior Data (2019 Oct/Nov)
- Storage layer: GCS `raw/kaggle/` → GCS `processed/clickstream/`
- Processing layer: Spark (Dataproc) for type cleaning and partition generation
- Warehouse: BigQuery external table + partitioned/clustered table
- Model layer: dbt (staging → marts)
- Consumption layer: Looker Studio dashboard
- Orchestration: 3 Airflow DAGs operated separately
- Visual element: End-to-End architecture diagram
- Presenter point: Layer separation ensures operability, incident response, and scalability

## Slide 5. Terraform Infrastructure Implementation
- Problem: Manual resource creation causes environment inconsistencies and omissions
- Solution: Declarative resource management with Terraform
- Implementation 1: GCS bucket creation (versioning, lifecycle rule, uniform access)
- Implementation 2: BigQuery dataset creation
- Operational benefit: Reproducible environment setup, reduced re-deployment time
- Risk/note: Separate operational policy when using `force_destroy` setting
- Visual element: Terraform resource relationship diagram
- Presenter point: IaC prevents "works only in dev" situations

## Slide 6. Airflow DAG Separation Strategy
- DAG 1: `clickstream_ingest_raw` (ingestion)
- DAG 2: `clickstream_spark_transform` (transformation)
- DAG 3: `clickstream_pipeline` (loading + modelling + validation)
- Problem: Putting all stages in one DAG makes it hard to trace failure locations
- Solution: DAG separation by responsibility + clear task ownership
- Operational benefit: Reduced failure blast radius, minimised re-run unit
- Common: Slack webhook alert on failure
- Visual element: DAG separation structure diagram
- Presenter point: Design that prioritises operability over technical complexity

## Slide 7. Ingest DAG — Detail
- Task 1: Download original zip with Kaggle CLI
- Task 2: Unzip with PythonOperator
- Task 3: Upload CSV files to GCS `raw/kaggle/`
- Data guarantee: Fail with FileNotFoundError if no files found
- Problem solved: Eliminates manual download/upload
- Outcome: Standardised source ingestion, reproducible monthly input
- Visual element: ingest task sequence
- Presenter point: Automating the "data inflow" stage is the starting point of pipeline reliability

## Slide 8. Spark Transform DAG — Detail
- Task 1: Upload `csv_parquet_job.py` to GCS `code/` path
- Task 2: Run Dataproc job (October)
- Task 3: Run Dataproc job (November)
- Config: Explicit performance params (executor instances/cores/memory, shuffle partitions)
- Operational control: `max_active_runs=1` to prevent duplicate execution
- Problem solved: Eliminates inefficiency of querying large CSVs directly
- Outcome: Converts data to analysis-friendly format (Parquet)
- Visual element: Dataproc execution flow
- Presenter point: Rationale for choosing distributed processing to handle data growth

## Slide 9. Core Spark Transformation Logic
- Bronze: Read all columns as strings to minimise raw data loss
- Typed: Cast key columns (`event_time`, `product_id`, `price`, `user_id`, etc.)
- Quality: Detect cast failures, label cause in `failure_reason` column
- Processed: Keep only rows with valid key identifiers (event_time/user_id/product_id)
- Schema stabilisation: Re-enforce Processed schema
- Time-series columns: Derive `event_date`, `event_month`, `event_month_date`
- Visual element: Bronze → Typed → Processed data flow
- Presenter point: The transformation logic acts as a data quality gate, not just a format conversion

## Slide 10. Storage Strategy and Re-run Stability
- Output format: Parquet + Snappy compression
- Partitions: `event_month`, `event_date`
- Problem: Risk of duplicate loading or inconsistency on re-run
- Solution: Delete target month partition path, then append
- Result: Month-level idempotent reprocessing possible
- Scalability: Same pattern reusable when adding new months
- Visual element: Partition overwrite strategy diagram
- Presenter point: Re-run strategy is a mandatory design element in production

## Slide 11. BigQuery DDL / Loading Structure
- SQL 1: `create_external_table.sql` (references GCS source)
- SQL 2: `create_partitioned_table.sql`
- SQL 3: `create_partitioned_clustered_table.sql`
- Problem: Must satisfy both raw accessibility and query performance/cost
- Solution: Two-layer operation — external table + optimised table
- Outcome: Stable analytical source and cost management foundation
- Visual element: BigQuery table layer structure
- Presenter point: DDL designed from an "analytical operations" perspective, not just "load first"

## Slide 12. dbt Staging Model (`stg_clickstream`)
- Input source: `clickstream_partitioned_clustered`
- Clean 1: Filter event type to `view/cart/purchase` only
- Clean 2: Remove nulls for `user_id`, `user_session`, `product_id`
- Derive: Extract `category_main` from `category_code`
- Standardise: Uniform column type casts
- Problem solved: Mitigates raw log quality variance
- Outcome: Guarantees stable input for downstream mart models
- Visual element: Before/after stg column comparison table
- Presenter point: Staging quality is the starting point of overall KPI reliability

## Slide 13. dbt Mart Models (`fct` / `mart`)
- `fct_funnel_events`: Generate per-session + per-product funnel flags
- Flags: `has_view`, `has_cart`, `has_purchase`, `funnel_stage`
- `mart_funnel`: Conversion rate aggregation by month/category/brand
- `mart_daily_funnel_kpi`: Daily KPI and session volume aggregation
- Metric consistency: Conversion rates calculated from a consistent population
- Outcome: BI-ready tables requiring no further transformation
- Visual element: dbt lineage + metric formula boxes
- Presenter point: Fact/mart separation supports both detailed diagnosis and executive metrics simultaneously

## Slide 14. Quality Management / Test Status
- dbt test: `accepted_values`, `not_null` applied
- Unit test 1: DAG import / task structure validation
- Unit test 2: Spark functions (casting / partitioning / schema) validation
- Integration test: Spark E2E flow validation with sample data
- TODO: load/resilience/performance tests are currently skipped
- Risk management: Explicitly state implemented vs not-implemented scope to avoid over-claiming
- Visual element: Test coverage matrix
- Presenter point: Present "what was validated and what remains" transparently

## Slide 15. Dashboard Insights and Actions
- Data sources: `mart_funnel`, `mart_daily_funnel_kpi`, `fct_funnel_events`
- Insight 1: Categories with low `view_to_cart_rate` → prioritise product detail / pricing review
- Insight 2: Periods with low `cart_to_purchase_rate` → prioritise payment UX / shipping fee experiments
- Insight 3: Sharp drops on specific dates → cross-check campaign quality / inventory / operational incidents
- Action 1: A/B test for product detail content improvements
- Action 2: Simplify checkout, experiment with coupons / shipping fees
- Action 3: Retarget cart-abandonment segments
- Prioritisation basis: Impact × implementation difficulty × lead time
- Visual element: Insight → Action mapping table
- Presenter point: Emphasise that analysis does not end at "discovery" but leads to execution

## Slide 16. Limitations and Improvement Roadmap
- Limitation 1: Batch-centric design limits near-real-time response
- Limitation 2: Advanced performance/resilience tests not yet completed
- Short-term (1–2 months): Strengthen monitoring/alerts, add more tests
- Medium-term (quarter): Add segment/cohort/retention analysis models
- Long-term (half-year+): Evaluate migration to streaming ingestion/processing architecture
- Expected benefit: Reduced operational risk + faster insight turnaround
- Conclusion: Incremental advancement toward a trustworthy data product
- Visual element: Short-medium-long term roadmap timeline
- Presenter point: Present the current state honestly and the expansion plan clearly without exaggeration
