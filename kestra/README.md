# Kestra Workflows

This directory contains the Kestra workflows for the clickstream pipeline.

## Flow Descriptions

### `gcp_kv.yaml`
- Initial setup flow that sets GCP-related KV values.
- Stores common settings such as project, region, bucket, and dataset in Kestra KV.

### `csv_gcs_load.yml`
- Downloads an external dataset and uploads CSV files to GCS.
- Unzips in a container, then iterates over generated CSVs to upload them.
- Upload path uses the bucket defined in KV.

## Prerequisites
- Kestra server/agent environment
- GCP service account JSON
- Required Secret/KV values registered

## General Settings (KV/Secret)
Register the following values in Kestra based on your environment.

- `GCP_PROJECT_ID`
- `GCP_LOCATION`
- `GCP_BUCKET_NAME`
- `GCP_DATASET`
- `GCP_CREDS` (full service account JSON)
- `KAGGLE_USERNAME` (if needed)
- `KAGGLE_API_KEY` (if needed)

## Usage
1) Upload flows to Kestra or connect via Git.
2) Enable the flows in the Kestra UI.
3) Set inputs/variables as needed and run.

## Notes
- See each YAML for detailed logic.
- Manage dataset/resource names via KV/Secret per environment.
