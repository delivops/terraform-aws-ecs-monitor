variable "cluster_name" {
  description = "The name of the ECS cluster"
  type        = string
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}

variable "environment" {
  description = "The environment for tagging purposes (e.g., dev, prod)"
  type        = string
}

variable "enable_crash_notifier" {
  description = "Whether to enable crash notifier for Slack notifications"
  type        = bool
  default     = false
}

variable "slack_bot_token" {
  description = "Slack bot token for sending notifications (shared by both crash notifier and daily summary)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "crash_notifier_slack_channel" {
  description = "Slack channel ID or name for sending crash notifications"
  type        = string
  default     = ""
}

variable "daily_summary_slack_channel" {
  description = "Slack channel ID or name for sending daily summary reports (defaults to crash_notifier_slack_channel if not set)"
  type        = string
  default     = ""
}

variable "crash_notifier_function_name" {
  description = "Name of the Lambda function for crash notifications"
  type        = string
  default     = ""
}

variable "crash_alert_aggregation_window_minutes" {
  description = "Sliding window in minutes used to aggregate repeat crashes of the same service into a single Slack parent message"
  type        = number
  default     = 30
}

variable "crash_alert_mode" {
  description = "How to surface repeat crashes within the aggregation window: 'edit' updates the parent only, 'thread' posts thread replies only, 'edit_and_thread' does both"
  type        = string
  default     = "edit_and_thread"

  validation {
    condition     = contains(["edit", "thread", "edit_and_thread"], var.crash_alert_mode)
    error_message = "crash_alert_mode must be one of: edit, thread, edit_and_thread."
  }
}

variable "enable_coralogix_integration" {
  description = "Whether to enable Coralogix integration for log retrieval"
  type        = bool
  default     = false
}

variable "coralogix_api_key" {
  description = "Coralogix API key for log retrieval"
  type        = string
  default     = ""
  sensitive   = true
}

variable "coralogix_region" {
  description = "Coralogix region (e.g., us, eu, eu2, ap, ap2)"
  type        = string
  default     = ""
}

variable "coralogix_account" {
  description = "Coralogix account name for generating UI links"
  type        = string
  default     = ""
}

variable "enable_elasticsearch_integration" {
  description = "Whether to enable Elasticsearch integration for log retrieval"
  type        = bool
  default     = false
}

variable "elasticsearch_endpoint" {
  description = "Elasticsearch endpoint URL (e.g., https://your-elasticsearch.com)"
  type        = string
  default     = ""
}

variable "elasticsearch_username" {
  description = "Elasticsearch username for authentication"
  type        = string
  default     = ""
}

variable "elasticsearch_password" {
  description = "Elasticsearch password for authentication"
  type        = string
  default     = ""
  sensitive   = true
}

variable "elasticsearch_index_pattern" {
  description = "Elasticsearch index pattern for searching logs (e.g., 'journey-logs-*')"
  type        = string
  default     = ""
}

variable "kibana_url" {
  description = "Kibana URL for generating UI links (e.g., 'https://kibana.company.com')"
  type        = string
  default     = ""
}

variable "enable_vpc_config" {
  description = "Whether to deploy Lambda function within a VPC (required for private Elasticsearch/Coralogix access)"
  type        = bool
  default     = false
}

variable "vpc_subnet_ids" {
  description = "List of subnet IDs for Lambda function (required if enable_vpc_config is true)"
  type        = list(string)
  default     = []
}

variable "vpc_security_group_ids" {
  description = "List of security group IDs for Lambda function (required if enable_vpc_config is true)"
  type        = list(string)
  default     = []
}

variable "enable_daily_summary" {
  description = "Whether to enable daily crash summary reports"
  type        = bool
  default     = false
}

variable "daily_summary_function_name" {
  description = "Name of the Lambda function for daily crash summaries"
  type        = string
  default     = ""
}

variable "daily_summary_schedule" {
  description = "Cron expression for daily summary schedule (default: 9 AM UTC daily)"
  type        = string
  default     = "cron(0 9 * * ? *)"
}

# ============================================================================
# Logs Anomalies Configuration
# ============================================================================

variable "enable_logs_anomalies" {
  description = "Whether to enable log anomaly detection and notifications"
  type        = bool
  default     = false
}

variable "logs_anomalies_function_name" {
  description = "Name of the Lambda function for log anomaly notifications"
  type        = string
  default     = ""
}

variable "logs_anomalies_schedule" {
  description = "Schedule expression for log anomaly checks (default: every 5 minutes)"
  type        = string
  default     = "rate(5 minutes)"
}

variable "logs_anomalies_slack_channel" {
  description = "Slack channel ID or name for sending log anomaly notifications"
  type        = string
  default     = ""
}

variable "logs_anomalies_log_group_prefix" {
  description = "Primary log group prefix to monitor for anomalies (defaults to /ecs/{cluster_name})"
  type        = string
  default     = ""
}

variable "logs_anomalies_additional_log_groups" {
  description = "Additional log group prefixes to monitor for anomalies"
  type        = list(string)
  default     = []
}

variable "logs_anomalies_priority_filter" {
  description = "Comma-separated list of anomaly priorities to notify (e.g., 'HIGH,MEDIUM')"
  type        = string
  default     = "HIGH,MEDIUM"
}

variable "logs_anomalies_dynamodb_table_name" {
  description = "Name of the DynamoDB table for anomaly notification state (defaults to {cluster_name}-logs-anomalies-state)"
  type        = string
  default     = ""
}

variable "logs_anomalies_ttl_days" {
  description = "Number of days to keep anomaly notification records in DynamoDB"
  type        = number
  default     = 7
}

# ============================================================================
# ECS Events Configuration
# ============================================================================

variable "enable_ecs_events" {
  description = "Whether to enable capturing all ECS events to a CloudWatch Log Group"
  type        = bool
  default     = false
}

variable "ecs_events_log_retention_days" {
  description = "Number of days to retain ECS events CloudWatch logs (defaults to log_retention_days if not set)"
  type        = number
  default     = null
}

variable "ecs_events_detail_types" {
  description = "List of ECS event detail-types to capture"
  type        = list(string)
  default = [
    "ECS Task State Change",
    "ECS Service Action",
    "ECS Container Instance State Change"
  ]
}
