# Secret Manager — defines secret containers (values populated manually or via CI)
locals {
  secrets = [
    "anthropic-api-key",
    "telegram-bot-token",
    "serper-api-key",
    "gmail-oauth-credentials",   # contents of credentials.json
    "gmail-oauth-token",         # contents of token.pickle (base64-encoded)
    "telegram-owner-chat-id",    # your personal Telegram chat ID
  ]
}

resource "google_secret_manager_secret" "secrets" {
  for_each  = toset(local.secrets)
  secret_id = each.key

  replication {
    auto {}
  }

  depends_on = [google_project_service.apis]
}

# Grant Cloud Run SA access to all secrets
resource "google_secret_manager_secret_iam_binding" "cloud_run_accessor" {
  for_each  = toset(local.secrets)
  secret_id = google_secret_manager_secret.secrets[each.key].secret_id
  role      = "roles/secretmanager.secretAccessor"
  members   = ["serviceAccount:${google_service_account.cloud_run_sa.email}"]
}
