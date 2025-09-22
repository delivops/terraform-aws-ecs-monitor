variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "cluster_name" {
  description = "The name of the ECS cluster to monitor"
  type        = string
}

variable "environment" {
  description = "The environment name (e.g., dev, staging, prod)"
  type        = string
  default     = "production"
}

variable "slack_bot_token" {
  description = "Slack Bot User OAuth Token (starts with xoxb-)"
  type        = string
  sensitive   = true
}

variable "slack_channel" {
  description = "Slack channel ID or name where crash notifications will be sent"
  type        = string
}

variable "elasticsearch_endpoint" {
  description = "Elasticsearch endpoint URL (e.g., https://your-elasticsearch.com)"
  type        = string
}

variable "elasticsearch_username" {
  description = "Elasticsearch username for authentication"
  type        = string
}

variable "elasticsearch_password" {
  description = "Elasticsearch password for authentication"
  type        = string
  sensitive   = true
}

variable "elasticsearch_index_pattern" {
  description = "Elasticsearch index pattern for searching logs (e.g., 'journey-logs-*')"
  type        = string
  default     = "*"
}

variable "kibana_url" {
  description = "Kibana URL for generating UI links (e.g., 'https://kibana.company.com')"
  type        = string
  default     = ""
}

variable "enable_vpc_config" {
  description = "Whether to deploy Lambda function within a VPC (required for private Elasticsearch access)"
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