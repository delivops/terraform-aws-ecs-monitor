variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "Name of the ECS cluster to monitor"
  type        = string
}

variable "environment" {
  description = "Environment name"
  type        = string
}

variable "slack_bot_token" {
  description = "Slack bot token for notifications"
  type        = string
  sensitive   = true
}

variable "slack_channel" {
  description = "Slack channel ID or name for notifications"
  type        = string
}
