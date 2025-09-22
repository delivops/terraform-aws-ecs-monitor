variable "cluster_name" {
  description = "The name of the ECS cluster to monitor"
  type        = string
}

variable "environment" {
  description = "Environment name for resource tagging"
  type        = string
  default     = "production"
}

variable "slack_bot_token" {
  description = "Slack bot token for sending notifications"
  type        = string
  sensitive   = true
}

variable "slack_channel" {
  description = "Slack channel for crash notifications and daily summaries"
  type        = string
}

variable "daily_summary_schedule" {
  description = "Cron expression for daily summary schedule"
  type        = string
  default     = "cron(0 9 * * ? *)"  # 9 AM UTC daily
}

variable "daily_summary_function_name" {
  description = "Custom name for the daily summary Lambda function"
  type        = string
  default     = ""
}

variable "crash_notifier_function_name" {
  description = "Custom name for the crash notification Lambda function"
  type        = string
  default     = ""
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}