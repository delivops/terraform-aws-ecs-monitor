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

variable "logs_anomalies_slack_channel" {
  description = "Slack channel for log anomaly notifications"
  type        = string
}

variable "logs_anomalies_schedule" {
  description = "Schedule expression for log anomaly checks"
  type        = string
  default     = "rate(5 minutes)"
}

variable "logs_anomalies_function_name" {
  description = "Custom name for the logs anomalies Lambda function"
  type        = string
  default     = ""
}

variable "logs_anomalies_log_group_prefix" {
  description = "Primary log group prefix to monitor (defaults to /ecs/{cluster_name})"
  type        = string
  default     = ""
}

variable "logs_anomalies_additional_log_groups" {
  description = "Additional log group prefixes to monitor for anomalies"
  type        = list(string)
  default     = []
}

variable "logs_anomalies_priority_filter" {
  description = "Comma-separated list of anomaly priorities to notify"
  type        = string
  default     = "HIGH,MEDIUM"
}

variable "logs_anomalies_service_channel_mapping" {
  description = "JSON string mapping service names to specific Slack channels"
  type        = string
  default     = "{}"
}

variable "logs_anomalies_dynamodb_table_name" {
  description = "Custom name for the DynamoDB state table"
  type        = string
  default     = ""
}

variable "logs_anomalies_ttl_days" {
  description = "Number of days to keep anomaly notification records"
  type        = number
  default     = 7
}

variable "log_retention_days" {
  description = "Number of days to retain CloudWatch logs"
  type        = number
  default     = 30
}
