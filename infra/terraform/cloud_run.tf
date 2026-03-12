locals {
  image = "${var.region}-docker.pkg.dev/${var.project_id}/${var.app_name}/app:latest"
}

# Main orchestrator + Telegram bot service
resource "google_cloud_run_v2_service" "orchestrator" {
  name     = var.app_name
  location = var.region

  template {
    service_account = google_service_account.cloud_run_sa.email

    scaling {
      min_instance_count = 1  # Keep warm for Telegram webhook
      max_instance_count = 20
    }

    timeout = "270s"

    containers {
      image = local.image

      resources {
        limits = {
          cpu    = "2"
          memory = "2Gi"
        }
      }

      # Secrets mounted as env vars — pin versions explicitly
      env {
        name = "ANTHROPIC_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "anthropic-api-key"
            version = "latest"  # Pin to specific version after first deploy
          }
        }
      }
      env {
        name = "TELEGRAM_BOT_TOKEN"
        value_source {
          secret_key_ref {
            secret  = "telegram-bot-token"
            version = "latest"
          }
        }
      }
      env {
        name = "SERPER_API_KEY"
        value_source {
          secret_key_ref {
            secret  = "serper-api-key"
            version = "latest"
          }
        }
      }
      env {
        name = "TELEGRAM_OWNER_CHAT_ID"
        value_source {
          secret_key_ref {
            secret  = "telegram-owner-chat-id"
            version = "latest"
          }
        }
      }

      # Non-secret config
      env {
        name  = "GCP_PROJECT_ID"
        value = var.project_id
      }
      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.telegram_fsm.host
      }
      env {
        name  = "CANVA_TEMPLATE_ID"
        value = "DAHDs0ivk0M"
      }

      liveness_probe {
        http_get {
          path = "/healthz"
        }
        initial_delay_seconds = 10
        period_seconds        = 30
      }
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_iam_binding.cloud_run_accessor,
  ]
}

# Allow unauthenticated invocations (Pub/Sub push + Telegram webhook)
resource "google_cloud_run_v2_service_iam_binding" "public" {
  name     = google_cloud_run_v2_service.orchestrator.name
  location = var.region
  role     = "roles/run.invoker"
  members  = ["allUsers"]
}

# Cloud Scheduler — renew Gmail watch daily at 06:00 UTC
resource "google_cloud_scheduler_job" "renew_gmail_watch" {
  name      = "renew-gmail-watch"
  schedule  = "0 6 * * *"
  time_zone = "UTC"
  region    = var.region

  http_target {
    uri         = "${google_cloud_run_v2_service.orchestrator.uri}/renew-watch"
    http_method = "POST"

    oidc_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }

  depends_on = [google_project_service.apis]
}

output "service_url" {
  value       = google_cloud_run_v2_service.orchestrator.uri
  description = "Cloud Run service URL — use this for Telegram webhook and Pub/Sub push endpoint"
}
