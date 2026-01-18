module "ecs_crash_monitor" {
  source = "../../"

  cluster_name = var.cluster_name
  environment  = var.environment

  # Enable log anomaly detection
  enable_logs_anomalies        = true
  slack_bot_token              = var.slack_bot_token
  logs_anomalies_slack_channel = var.logs_anomalies_slack_channel

  # Log anomaly configuration
  logs_anomalies_schedule                = var.logs_anomalies_schedule
  logs_anomalies_function_name           = var.logs_anomalies_function_name
  logs_anomalies_log_group_prefix        = var.logs_anomalies_log_group_prefix
  logs_anomalies_additional_log_groups   = var.logs_anomalies_additional_log_groups
  logs_anomalies_priority_filter         = var.logs_anomalies_priority_filter
  logs_anomalies_service_channel_mapping = var.logs_anomalies_service_channel_mapping
  logs_anomalies_dynamodb_table_name     = var.logs_anomalies_dynamodb_table_name
  logs_anomalies_ttl_days                = var.logs_anomalies_ttl_days

  # Optional: Enable crash notifier as well
  # enable_crash_notifier        = true
  # crash_notifier_slack_channel = var.logs_anomalies_slack_channel

  # Optional customizations
  log_retention_days = var.log_retention_days
}
