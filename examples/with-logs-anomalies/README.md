# ECS Crash Monitor with Log Anomaly Detection Example

This example demonstrates how to deploy the ECS crash monitoring module with CloudWatch Logs anomaly detection and Slack notifications.

## Features

- **Automatic anomaly detection**: Monitors CloudWatch Logs Anomaly Detectors for matching log groups
- **Multi-prefix support**: Monitor multiple log group patterns (e.g., `/ecs/cluster`, `/aws/lambda/`)
- **Deduplication**: Uses DynamoDB to track notified anomalies and prevent duplicate alerts
- **Priority filtering**: Only notify for HIGH and MEDIUM priority anomalies (configurable)
- **Service-specific channels**: Route anomaly alerts to different Slack channels based on service name
- **Scheduled checks**: Runs every 5 minutes by default (configurable)

## Prerequisites

Before using this example, you must have:

1. **CloudWatch Logs Anomaly Detectors configured** for your log groups
   - Go to CloudWatch Console → Logs → Anomaly Detectors
   - Create detectors for the log groups you want to monitor

2. **Slack Bot with required permissions**:
   - `chat:write` - Send messages to channels

## Usage

1. Copy the example tfvars file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your values:
   ```hcl
   cluster_name                 = "my-production-cluster"
   slack_bot_token              = "xoxb-your-bot-token-here"
   logs_anomalies_slack_channel = "#log-anomalies"
   environment                  = "production"
   ```

3. Initialize and apply:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## Slack Bot Setup

To use this example, you'll need a Slack bot with the following permissions:
- `chat:write` - Send messages to channels

### Creating a Slack Bot

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "Log Anomaly Monitor") and select your workspace
4. Go to "OAuth & Permissions" → "Scopes" → "Bot Token Scopes"
5. Add the required scope: `chat:write`
6. Install the app to your workspace
7. Copy the "Bot User OAuth Token" (starts with `xoxb-`)
8. Invite the bot to your target channel: `/invite @your-bot-name`

## Configuration Options

### Log Group Prefixes

By default, the Lambda monitors log groups matching `/ecs/{cluster_name}`. You can customize this:

```hcl
# Custom primary prefix
logs_anomalies_log_group_prefix = "/ecs/my-cluster"

# Additional prefixes to monitor
logs_anomalies_additional_log_groups = [
  "/aws/lambda/",
  "/custom/app-logs/",
  "/ecs/other-cluster/"
]
```

### Priority Filtering

Control which anomaly priorities trigger notifications:

```hcl
# Only HIGH priority (most critical)
logs_anomalies_priority_filter = "HIGH"

# HIGH and MEDIUM (default)
logs_anomalies_priority_filter = "HIGH,MEDIUM"

# All priorities
logs_anomalies_priority_filter = "HIGH,MEDIUM,LOW"
```

### Service-Specific Channels

Route anomalies to different Slack channels based on service name:

```hcl
logs_anomalies_service_channel_mapping = jsonencode({
  "api-service"    = "#api-alerts"
  "worker-service" = "#worker-alerts"
  "auth-service"   = "#security-alerts"
})
```

### Schedule

Change how often the Lambda checks for new anomalies:

```hcl
# Every 5 minutes (default)
logs_anomalies_schedule = "rate(5 minutes)"

# Every 15 minutes
logs_anomalies_schedule = "rate(15 minutes)"

# Every hour
logs_anomalies_schedule = "rate(1 hour)"

# Cron expression (every 10 minutes during business hours)
logs_anomalies_schedule = "cron(0/10 9-17 ? * MON-FRI *)"
```

## Example Slack Notification

When an anomaly is detected, you'll receive a Slack message like:

```
🔍 Log Anomaly Detected

Service: api-service
Priority: 🔴 HIGH
First Seen: 2026-01-18 10:30:00 UTC
Last Seen: 2026-01-18 10:45:00 UTC

Description:
Unusual increase in error log frequency detected

Pattern:
ERROR: Connection refused to database server *

Sample Logs:
• ERROR: Connection refused to database server prod-db-1
• ERROR: Connection refused to database server prod-db-2
• ERROR: Connection refused to database server prod-db-1

View in CloudWatch Console
```

## Outputs

After applying, you can access these outputs:

```hcl
# Lambda function details
output "logs_anomalies_lambda_arn" {}
output "logs_anomalies_lambda_name" {}

# DynamoDB table for state tracking
output "logs_anomalies_dynamodb_table_name" {}
output "logs_anomalies_dynamodb_table_arn" {}

# EventBridge schedule rule
output "logs_anomalies_schedule_rule_name" {}
```

## Combining with Other Features

You can enable log anomaly detection alongside other monitoring features:

```hcl
module "ecs_crash_monitor" {
  source = "../../"

  cluster_name    = var.cluster_name
  environment     = var.environment
  slack_bot_token = var.slack_bot_token

  # Real-time crash notifications
  enable_crash_notifier        = true
  crash_notifier_slack_channel = "#ecs-crashes"

  # Daily summary reports
  enable_daily_summary          = true
  daily_summary_slack_channel   = "#ecs-reports"

  # Log anomaly detection
  enable_logs_anomalies         = true
  logs_anomalies_slack_channel  = "#log-anomalies"
}
```

## Troubleshooting

### No anomalies detected

1. Verify CloudWatch Logs Anomaly Detectors are configured for your log groups
2. Check the Lambda logs in CloudWatch for errors
3. Ensure log group prefixes match your detector configuration

### Duplicate notifications

The Lambda uses DynamoDB to track notified anomalies. If you're seeing duplicates:
1. Check the DynamoDB table for entries
2. Verify TTL is configured correctly
3. Check for Lambda timeout issues

### Permission errors

Ensure the Lambda has permissions for:
- `logs:ListLogAnomalyDetectors`
- `logs:ListAnomalies`
- `logs:DescribeLogGroups`
- `dynamodb:GetItem`
- `dynamodb:PutItem`
