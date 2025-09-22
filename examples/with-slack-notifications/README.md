# ECS Crash Monitor with Slack Notifications Example

This example demonstrates the ECS Crash Monitor module with enriched Slack notifications enabled using Slack Bot API.

## Features

- CloudWatch logging for crash events
- Lambda function for data enrichment
- Slack notifications with rich formatting using Bot API
- Container logs attached as downloadable text files
- Service health status information
- Enhanced file attachment capabilities

## Prerequisites

1. **Slack Bot Token**: Create a Slack app and get a bot token:
   - Go to https://api.slack.com/apps
   - Create a new app or use existing
   - Go to "OAuth & Permissions"
   - Add the following Bot Token Scopes:
     - `chat:write` - Send messages
     - `files:write` - Upload files  
   - Install the app to your workspace
   - Copy the "Bot User OAuth Token" (starts with `xoxb-`)
   - Invite the bot to your target channel

## Usage

1. Copy the example tfvars file:
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. Update `terraform.tfvars` with your values:
   - Set your Slack bot token (`slack_bot_token`)
   - Set your target channel (`slack_channel`) - use channel name like `#ecs-alerts` or channel ID
   - Configure cluster name and environment

3. Apply the configuration:
   ```bash
   terraform init
   terraform plan
   terraform apply
   ```

## What You'll Receive

When an ECS task crashes, you'll receive a Slack message with:
- Rich formatting with blocks and colors
- Timestamp and basic crash information
- Service health status (running/desired counts)
- Full container logs as an attached text file (no size limits)
- Task ID for debugging
- Exit code and crash reason

## Bot vs Webhook Advantages

This example uses Slack Bot API instead of webhooks for:
- **File Attachments**: Full logs in downloadable files
- **Clean Messages**: Main alert stays concise and readable
- **No Size Limits**: Large log outputs don't break notifications
- **Better Threading**: Potential for future threaded conversations

## Customization

The Lambda function can be extended to:
- Add more AWS API calls for additional context
- Integrate with other alerting systems
- Filter or transform messages based on criteria
- Add custom enrichment logic