# ECS Crash Monitor with Daily Summary Example

This example demonstrates how to deploy the ECS crash monitoring module with both real-time crash notifications and daily summary reports.

## Features

- **Real-time crash notifications**: Immediate Slack alerts when tasks crash
- **Daily summary reports**: Comprehensive daily analysis at 9 AM UTC
- **Comprehensive analysis**: Crash patterns, trends, and affected services
- **Zero-crash celebrations**: Positive messaging when no crashes occur

## Usage

1. Copy the example tfvars file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Edit `terraform.tfvars` with your values:
   ```hcl
   cluster_name     = "my-production-cluster"
   slack_bot_token  = "xoxb-your-bot-token-here"
   slack_channel    = "#ecs-alerts"
   environment      = "production"
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
- `files:write` - Upload log files as attachments

### Creating a Slack Bot

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click "Create New App" → "From scratch"
3. Name your app (e.g., "ECS Monitor") and select your workspace
4. Go to "OAuth & Permissions" → "Scopes" → "Bot Token Scopes"
5. Add the required scopes: `chat:write` and `files:write`
6. Install the app to your workspace
7. Copy the "Bot User OAuth Token" (starts with `xoxb-`)
8. Invite the bot to your target channel: `/invite @your-bot-name`

## Daily Summary Features

The daily summary includes:

- **📊 Overview**: Total crashes and affected services
- **🔍 Key Insights**: 
  - Top crash reasons (with counts)
  - Most affected services (with crash counts)  
  - Common exit codes (with frequencies)
- **🕐 Hourly Distribution**: When crashes occurred (UTC timezone)
- **🔧 Affected Services**: Complete list with individual crash counts
- **✅ Zero-crash Days**: Celebratory messages when no crashes occurred

## Customization

### Schedule

Change the daily summary time by modifying `daily_summary_schedule`:

```hcl
# 8 AM UTC daily
daily_summary_schedule = "cron(0 8 * * ? *)"

# 6 PM UTC on weekdays only
daily_summary_schedule = "cron(0 18 ? * MON-FRI *)"

# Twice daily: 9 AM and 6 PM UTC
# Note: You'll need to create two separate modules for this
```

### Lambda Function Names

Customize function names for better organization:

```hcl
crash_notifier_function_name    = "prod-ecs-crash-notifier"
daily_summary_function_name     = "prod-ecs-daily-summary"
```

## Example Daily Summary

Here's what a daily summary might look like in Slack:

```
🚨 Daily Crash Summary - 2024-03-15

⚠️ 8 crashes detected across 3 service(s) in the production cluster.

🔍 Key Insights

Top Crash Reasons:
• Task failed container health checks: 4 crashes
• OutOfMemoryError: Killed due to memory usage: 3 crashes  
• Exit code 1: 1 crash

Most Affected Services:
• web-app: 5 crashes
• background-worker: 2 crashes
• api-service: 1 crash

Common Exit Codes:
• Exit 137: 3 occurrences
• Exit 1: 4 occurrences
• Exit 0: 1 occurrence

🕐 Hourly Distribution (UTC):
• 02:00 - 1 crash
• 08:00 - 3 crashes
• 14:00 - 2 crashes
• 20:00 - 2 crashes

🔧 Affected Services:
• web-app - 5 crashes
• background-worker - 2 crashes  
• api-service - 1 crash

Cluster: production | Generated: 2024-03-16 09:00:01 UTC
```

## Cost Considerations

This example adds minimal AWS costs:
- **CloudWatch Logs**: ~$0.50/GB ingested, ~$0.03/GB stored
- **Lambda**: ~$0.20 per 1M requests + $0.0000166667 per GB-second
- **EventBridge**: ~$1.00 per million events

For a typical cluster with a few crashes per day, expect <$5/month total cost.

## Security

The module follows AWS security best practices:
- Least-privilege IAM roles and policies
- Encrypted Lambda environment variables for sensitive data
- VPC support for private network access
- CloudWatch Logs encryption at rest