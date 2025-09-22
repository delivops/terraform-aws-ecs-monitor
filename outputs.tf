output "log_group_name" {
  description = "Name of the CloudWatch Log Group for crash events"
  value       = aws_cloudwatch_log_group.crash_events.name
}

output "log_group_arn" {
  description = "ARN of the CloudWatch Log Group for crash events"
  value       = aws_cloudwatch_log_group.crash_events.arn
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule monitoring ECS task state changes"
  value       = aws_cloudwatch_event_rule.ecs_task_state_changes.name
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule monitoring ECS task state changes"
  value       = aws_cloudwatch_event_rule.ecs_task_state_changes.arn
}

output "log_resource_policy_name" {
  description = "Name of the CloudWatch Log resource policy allowing EventBridge access"
  value       = aws_cloudwatch_log_resource_policy.crash_events_policy.policy_name
}

output "crash_notifier_lambda_arn" {
  description = "ARN of the crash notifier Lambda function (if enabled)"
  value       = var.enable_crash_notifier ? module.crash_notifier_lambda[0].lambda_function_arn : null
}

output "crash_notifier_lambda_name" {
  description = "Name of the crash notifier Lambda function (if enabled)"
  value       = var.enable_crash_notifier ? module.crash_notifier_lambda[0].lambda_function_name : null
}

output "daily_summary_lambda_arn" {
  description = "ARN of the daily summary Lambda function (if enabled)"
  value       = var.enable_daily_summary ? module.daily_summary_lambda[0].lambda_function_arn : null
}

output "daily_summary_lambda_name" {
  description = "Name of the daily summary Lambda function (if enabled)"
  value       = var.enable_daily_summary ? module.daily_summary_lambda[0].lambda_function_name : null
}

output "daily_summary_schedule_rule_name" {
  description = "Name of the EventBridge rule for daily summary schedule (if enabled)"
  value       = var.enable_daily_summary ? aws_cloudwatch_event_rule.daily_summary_schedule[0].name : null
}