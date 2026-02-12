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

module "ecs_monitor" {
  source = "../../"

  cluster_name       = var.cluster_name
  environment        = var.environment
  enable_ecs_events  = true
  log_retention_days = 14

  # Optionally also enable crash notifications
  # enable_crash_notifier        = true
  # slack_bot_token              = "xoxb-your-token"
  # crash_notifier_slack_channel = "#ecs-alerts"
}

output "ecs_events_log_group_name" {
  description = "CloudWatch Log Group name for all ECS events"
  value       = module.ecs_monitor.ecs_events_log_group_name
}

output "ecs_events_log_group_arn" {
  description = "CloudWatch Log Group ARN for all ECS events"
  value       = module.ecs_monitor.ecs_events_log_group_arn
}

output "ecs_events_rule_arn" {
  description = "EventBridge rule ARN for all ECS events"
  value       = module.ecs_monitor.ecs_events_rule_arn
}
