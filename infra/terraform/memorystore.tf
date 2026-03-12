# Cloud Memorystore (Redis) for Telegram bot FSM state
resource "google_redis_instance" "telegram_fsm" {
  name           = "${var.app_name}-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region

  redis_version  = "REDIS_7_0"
  display_name   = "Telegram FSM State"

  depends_on = [google_project_service.apis]
}

output "redis_host" {
  value       = google_redis_instance.telegram_fsm.host
  description = "Redis host — add to Cloud Run env as REDIS_HOST"
}
