terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "4.51.0"
    }
  }
}

provider "google" {
  credentials = file("cred/clickstream-sa.json") 
  project = var.project_id
  region  = var.region
}



resource "google_storage_bucket" "data-lake-bucket" {
  name          = "${var.project_id}-clickstream-data"
  location      = var.location

  # Optional, but recommended settings:
  storage_class = "STANDARD"
  uniform_bucket_level_access = true

  versioning {
    enabled     = true
  }

  lifecycle_rule {
    action {
      type = "Delete"
    }
    condition {
      age = 30  // days
    }
  }

  force_destroy = true
}


resource "google_bigquery_dataset" "dataset" {
  dataset_id = var.dataset_id
  project    = var.project_id
  location   = var.location
}