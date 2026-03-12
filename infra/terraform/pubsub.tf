# Pub/Sub topic for Gmail push notifications
resource "google_pubsub_topic" "gmail_notifications" {
  name = "gmail-notifications"
  depends_on = [google_project_service.apis]
}

# Grant Gmail service account permission to publish to the topic
# Note: gmail-api-push@system.gserviceaccount.com is Google-managed,
# it does not appear in IAM console — this is expected.
resource "google_pubsub_topic_iam_binding" "gmail_publisher" {
  topic = google_pubsub_topic.gmail_notifications.name
  role  = "roles/pubsub.publisher"
  members = [
    "serviceAccount:gmail-api-push@system.gserviceaccount.com",
  ]
}

# Push subscription → Cloud Run orchestrator endpoint
resource "google_pubsub_subscription" "gmail_push_sub" {
  name  = "gmail-push-sub"
  topic = google_pubsub_topic.gmail_notifications.name

  push_config {
    push_endpoint = "${google_cloud_run_v2_service.orchestrator.uri}/pubsub/push"

    oidc_token {
      service_account_email = google_service_account.cloud_run_sa.email
    }
  }

  ack_deadline_seconds = 60

  retry_policy {
    minimum_backoff = "10s"
    maximum_backoff = "300s"
  }

  depends_on = [google_project_service.apis]
}
