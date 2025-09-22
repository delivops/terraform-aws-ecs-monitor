terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

module "ecs_crash_monitor" {
  source = "../../"

  cluster_name                       = var.cluster_name
  environment                        = var.environment
  enable_crash_notifier              = true
  slack_bot_token                    = var.slack_bot_token
  crash_notifier_slack_channel       = var.slack_channel
  enable_elasticsearch_integration   = true
  elasticsearch_endpoint             = var.elasticsearch_endpoint
  elasticsearch_username             = var.elasticsearch_username
  elasticsearch_password             = var.elasticsearch_password
  elasticsearch_index_pattern        = var.elasticsearch_index_pattern
  kibana_url                         = var.kibana_url
  enable_vpc_config                  = var.enable_vpc_config
  vpc_subnet_ids                     = var.vpc_subnet_ids
  vpc_security_group_ids             = var.vpc_security_group_ids
}

# Outputs
output "log_group_name" {
  description = "CloudWatch Log Group name for crash events"
  value       = module.ecs_crash_monitor.log_group_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN for notifications"
  value       = module.ecs_crash_monitor.lambda_function_arn
}

output "eventbridge_rule_name" {
  description = "EventBridge rule name"
  value       = module.ecs_crash_monitor.eventbridge_rule_name
}