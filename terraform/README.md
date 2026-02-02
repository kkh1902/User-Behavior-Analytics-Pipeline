## Overview
This directory provisions the GCP resources required for the clickstream pipeline using Terraform.

## Provisioned Resources
- GCS bucket: `${project_id}-clickstream-data`
  - Versioning enabled
  - Lifecycle rule to delete objects older than 30 days
  - `uniform_bucket_level_access` enabled
  - `force_destroy = true` (bucket can be destroyed even if not empty)
- BigQuery dataset: `dataset_id`

## Prerequisites
- Terraform installed
- GCP project created with billing enabled
- Service account key file ready
  - Path: `cred/clickstream-sa.json`
  - Minimum permissions: create GCS buckets and BigQuery datasets

## Usage
```bash
# Run from the terraform directory
cd terraform

terraform init
terraform plan
terraform apply
```

## Variables
You can use defaults in `variables.tf` or override with `-var` / `*.tfvars`.

| Variable | Description | Default |
|----------|-------------|---------|
| project_id | GCP Project ID | clickstream-pipeline-484705 |
| region | GCP Region | asia-northeast3 |
| location | GCS/BigQuery Location | asia-northeast3 |
| dataset_id | BigQuery Dataset ID | clickstream |

## Destroy
```bash
cd terraform
terraform destroy
```

## Notes
- The path `cred/clickstream-sa.json` is hardcoded in Terraform. Update `main.tf` if you use a different path.
- The bucket has `force_destroy = true`, so `terraform destroy` will delete all objects in the bucket.
