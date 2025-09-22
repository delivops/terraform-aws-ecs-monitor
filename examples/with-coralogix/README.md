# ECS Crash Monitor with Coralogix Integration Example

This example demonstrates the ECS Crash Monitor module with Coralogix integration for log retrieval and enriched Slack notifications.

## Features

- CloudWatch logging for crash events
- Lambda function for data enrichment
- **Coralogix Integration**: Automatically retrieve logs from Coralogix when available
- **Hybrid Log Support**: Falls back to CloudWatch if Coralogix is not available
- **Enhanced Slack Notifications**: Include Coralogix UI links for easy log access
- Rich formatting with blocks and file attachments

## Prerequisites

1. **Slack Bot Token**: Same setup as the basic Slack example
2. **Coralogix API Key**: 
   - Go to your Coralogix dashboard
   - Navigate to Data Flow → API Keys
   - Create a new API key with "Query" permissions
   - Copy the key (starts with `cxtp_`)

## Configuration

The module will automatically detect when to use Coralogix vs CloudWatch based on:

1. **Coralogix Configuration**: If `enable_coralogix_integration = true` and all Coralogix variables are provided
2. **Task Definition**: The actual logging configuration in your ECS task definition

### Coralogix Requirements

For Coralogix integration to work, your ECS tasks must be configured to send logs to Coralogix with the `ecs_task_arn` field included in the log metadata.

Example task definition logging configuration:
```json
{
  "logConfiguration": {
    "logDriver": "fluentd",
    "options": {
      "fluentd-address": "your-fluentd-endpoint",
      "tag": "ecs.{{.Name}}",
      "fluentd-async-connect": "true"
    }
  }
}
```

The Coralogix integration expects logs to include the `ecs_task_arn` field for filtering.

## Usage

1. Copy the example tfvars file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Update `terraform.tfvars` with your values:
   - Slack configuration (same as other examples)
   - Coralogix API key, region, and account name
   - Set your cluster name and environment

3. Apply the configuration:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## How It Works

1. **Log Detection**: When a crash occurs, the Lambda function checks:
   - If Coralogix integration is enabled and configured
   - The task definition's logging configuration

2. **Log Retrieval**: 
   - **Coralogix**: Uses the DataPrime query API to fetch logs filtered by `ecs_task_arn`
   - **CloudWatch**: Falls back to standard CloudWatch Logs API
   - **Hybrid**: Tries Coralogix first, falls back to CloudWatch if no logs found

3. **Enhanced Notifications**: Slack notifications include:
   - Log source indicator (Coralogix or CloudWatch)
   - Clickable link to Coralogix UI when logs come from Coralogix
   - All logs attached as downloadable files

## Coralogix UI Links

When logs are retrieved from Coralogix, the Slack notification will include a direct link to the Coralogix UI with a pre-filtered query showing only logs for the crashed task.

Example generated link:
```
https://your-account.app.eu2.coralogix.com/#/query-new/archive-logs?time=from:now-1h,to:now&querySyntax=dataprime&query=source%20logs%20%7C%20filter%20$d.ecs_task_arn%20~%20'arn:aws:ecs:...'
```

## Environment Variables

The Lambda function receives these Coralogix-related environment variables:
- `ENABLE_CORALOGIX_INTEGRATION`: Whether Coralogix integration is enabled
- `CORALOGIX_API_KEY`: API key for Coralogix DataPrime queries
- `CORALOGIX_REGION`: Coralogix region (eu2, us, etc.)
- `CORALOGIX_ACCOUNT`: Account name for UI link generation

## Troubleshooting

### No Logs from Coralogix
- Verify the API key has "Query" permissions
- Check that your logs include the `ecs_task_arn` field
- Ensure the Coralogix region and account are correct
- The system will automatically fall back to CloudWatch if available

### Coralogix UI Links Not Working
- Verify the `coralogix_account` variable matches your account name exactly
- Check the `coralogix_region` is correct for your setup
