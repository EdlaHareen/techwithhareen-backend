terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
  # Uncomment to store state remotely in GCS (recommended for production)
  # backend "gcs" {
  #   bucket = "YOUR_PROJECT_ID-tfstate"
  #   prefix = "insta-handler"
  # }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "app_name" {
  description = "Application name prefix"
  type        = string
  default     = "insta-handler"
}

# Enable required APIs
resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "pubsub.googleapis.com",
    "firestore.googleapis.com",
    "secretmanager.googleapis.com",
    "redis.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "gmail.googleapis.com",
  ])
  service            = each.key
  disable_on_destroy = false
}

# Artifact Registry for Docker images
resource "google_artifact_registry_repository" "app" {
  location      = var.region
  repository_id = var.app_name
  format        = "DOCKER"
  depends_on    = [google_project_service.apis]
}

# Service account for Cloud Run
resource "google_service_account" "cloud_run_sa" {
  account_id   = "${var.app_name}-sa"
  display_name = "Insta Handler Cloud Run SA"
}
