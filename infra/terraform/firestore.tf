# Firestore native mode database
resource "google_firestore_database" "default" {
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.apis]
}

# Grant Cloud Run SA read/write access to Firestore
resource "google_project_iam_binding" "firestore_user" {
  project = var.project_id
  role    = "roles/datastore.user"
  members = ["serviceAccount:${google_service_account.cloud_run_sa.email}"]
}
