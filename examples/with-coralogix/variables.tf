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

variable "coralogix_api_key" {
  description = "Coralogix API key for log retrieval"
  type        = string
  sensitive   = true
}

variable "coralogix_region" {
  description = "Coralogix region (e.g., us, eu, eu2, ap, ap2)"
  type        = string
}

variable "coralogix_account" {
  description = "Coralogix account name for generating UI links"
  type        = string
}

variable "enable_vpc_config" {
  description = "Whether to deploy Lambda function within a VPC (required for private Coralogix access)"
  type        = bool
  default     = false
}

variable "vpc_subnet_ids" {
  description = "List of private subnet IDs for Lambda function"
  type        = list(string)
  default     = []
}

variable "vpc_security_group_ids" {
  description = "List of security group IDs for Lambda function"
  type        = list(string)
  default     = []
}