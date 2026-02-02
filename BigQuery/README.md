# BigQuery

This folder contains SQL for loading clickstream data into BigQuery, creating performance-optimized analytics tables, and building aggregate tables for Looker Studio dashboards.

### Key files
- clickstream_analysis.sql: Builds hourly event-type aggregates for visualization
- create_external_table.sql: Creates external tables over GCS Parquet/CSV data
- create_partitioned_table.sql: Creates partitioned tables
- created_partitioned_clustered_table.sql: Creates partitioned + clustered tables

### Typical order
1. create_external_table.sql
2. create_partitioned_table.sql or created_partitioned_clustered_table.sql
3. clickstream_analysis.sql

### Notes
- Update project/dataset names for your environment.
- Adjust partition and clustering keys based on query patterns.
