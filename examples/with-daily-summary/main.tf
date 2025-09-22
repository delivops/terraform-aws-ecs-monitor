module "ecs_crash_monitor" {
  source = "../../"

  cluster_name               = var.cluster_name
  environment               = var.environment
  
  # Enable both real-time notifications and daily summaries
  enable_crash_notifier         = true
  slack_bot_token               = var.slack_bot_token
  crash_notifier_slack_channel  = var.slack_channel
  
  # Daily summary configuration
  enable_daily_summary          = true
  daily_summary_schedule        = var.daily_summary_schedule
  daily_summary_function_name   = var.daily_summary_function_name
  # Optional: use a different channel for daily summaries
  # daily_summary_slack_channel = "#ecs-reports"
  
  # Optional customizations
  crash_notifier_function_name = var.crash_notifier_function_name
  log_retention_days          = var.log_retention_days
}