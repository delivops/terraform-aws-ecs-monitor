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

  cluster_name                 = var.cluster_name
  environment                  = var.environment
  enable_crash_notifier        = true
  slack_bot_token              = var.slack_bot_token
  crash_notifier_slack_channel = var.slack_channel
}

# Outputs
output "log_group_name" {
  description = "CloudWatch Log Group name for crash events"
  value       = module.ecs_crash_monitor.log_group_name
}

output "lambda_function_arn" {
  description = "Lambda function ARN for notifications"
  value       = module.ecs_crash_monitor.crash_notifier_lambda_arn
}

output "eventbridge_rule_name" {
  description = "EventBridge rule name"
  value       = module.ecs_crash_monitor.eventbridge_rule_name
}
