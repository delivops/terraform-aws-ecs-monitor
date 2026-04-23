output "log_group_name" {
  description = "Name of the CloudWatch Log Group for crash events"
  value       = local.enable_crash_monitoring ? aws_cloudwatch_log_group.crash_events[0].name : null
}

output "log_group_arn" {
  description = "ARN of the CloudWatch Log Group for crash events"
  value       = local.enable_crash_monitoring ? aws_cloudwatch_log_group.crash_events[0].arn : null
}

output "eventbridge_rule_name" {
  description = "Name of the EventBridge rule monitoring ECS task state changes"
  value       = local.enable_crash_monitoring ? aws_cloudwatch_event_rule.ecs_task_state_changes[0].name : null
}

output "eventbridge_rule_arn" {
  description = "ARN of the EventBridge rule monitoring ECS task state changes"
  value       = local.enable_crash_monitoring ? aws_cloudwatch_event_rule.ecs_task_state_changes[0].arn : null
}

output "log_resource_policy_name" {
  description = "Name of the CloudWatch Log resource policy allowing EventBridge access"
  value       = local.enable_crash_monitoring ? aws_cloudwatch_log_resource_policy.crash_events_policy[0].policy_name : null
}

output "crash_notifier_lambda_arn" {
  description = "ARN of the crash notifier Lambda function (if enabled)"
  value       = var.enable_crash_notifier ? module.crash_notifier_lambda[0].lambda_function_arn : null
}

output "crash_notifier_lambda_name" {
  description = "Name of the crash notifier Lambda function (if enabled)"
  value       = var.enable_crash_notifier ? module.crash_notifier_lambda[0].lambda_function_name : null
}

output "crash_alert_state_table_name" {
  description = "Name of the DynamoDB table used to aggregate crash-loop alerts (if enabled)"
  value       = var.enable_crash_notifier ? aws_dynamodb_table.crash_alert_state[0].name : null
}

output "crash_alert_state_table_arn" {
  description = "ARN of the DynamoDB table used to aggregate crash-loop alerts (if enabled)"
  value       = var.enable_crash_notifier ? aws_dynamodb_table.crash_alert_state[0].arn : null
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

# ============================================================================
# Logs Anomalies Outputs
# ============================================================================

output "logs_anomalies_lambda_arn" {
  description = "ARN of the logs anomalies Lambda function (if enabled)"
  value       = var.enable_logs_anomalies ? module.logs_anomalies_lambda[0].lambda_function_arn : null
}

output "logs_anomalies_lambda_name" {
  description = "Name of the logs anomalies Lambda function (if enabled)"
  value       = var.enable_logs_anomalies ? module.logs_anomalies_lambda[0].lambda_function_name : null
}

output "logs_anomalies_dynamodb_table_name" {
  description = "Name of the DynamoDB table for logs anomalies state (if enabled)"
  value       = var.enable_logs_anomalies ? aws_dynamodb_table.logs_anomalies_state[0].name : null
}

output "logs_anomalies_dynamodb_table_arn" {
  description = "ARN of the DynamoDB table for logs anomalies state (if enabled)"
  value       = var.enable_logs_anomalies ? aws_dynamodb_table.logs_anomalies_state[0].arn : null
}

output "logs_anomalies_schedule_rule_name" {
  description = "Name of the EventBridge rule for logs anomalies schedule (if enabled)"
  value       = var.enable_logs_anomalies ? aws_cloudwatch_event_rule.logs_anomalies_schedule[0].name : null
}

# ============================================================================
# ECS Events Outputs
# ============================================================================

output "ecs_events_log_group_name" {
  description = "Name of the CloudWatch Log Group for all ECS events (if enabled)"
  value       = var.enable_ecs_events ? aws_cloudwatch_log_group.ecs_events[0].name : null
}

output "ecs_events_log_group_arn" {
  description = "ARN of the CloudWatch Log Group for all ECS events (if enabled)"
  value       = var.enable_ecs_events ? aws_cloudwatch_log_group.ecs_events[0].arn : null
}

output "ecs_events_rule_arn" {
  description = "ARN of the EventBridge rule for all ECS events (if enabled)"
  value       = var.enable_ecs_events ? aws_cloudwatch_event_rule.ecs_all_events[0].arn : null
}