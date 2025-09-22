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

  cluster_name       = var.cluster_name
  environment        = var.environment
}

# Example: Query the outputs
output "log_group_name" {
  description = "CloudWatch Log Group name for crash events"
  value       = module.ecs_crash_monitor.log_group_name
}

output "eventbridge_rule_arn" {
  description = "EventBridge rule ARN"
  value       = module.ecs_crash_monitor.eventbridge_rule_arn
}
