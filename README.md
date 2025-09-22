
[![DelivOps banner](https://raw.githubusercontent.com/delivops/.github/main/images/banner.png?raw=true)](https://delivops.com)


# Terraform ECS Monitor Module

A Terraform module that monitors ECS service crashes and provides comprehensive logging and enriched Slack notification capabilities.

## Features

- **Automated Crash Detection**: Monitors ECS task state changes and detects crashes (non-zero exit codes)
- **CloudWatch Logging**: Stores crash events in dedicated CloudWatch log groups
- **Daily Summary Reports**: Automated daily analysis and summary of crash events with insights and trends
- **Coralogix Integration**: Optional integration for retrieving logs from Coralogix platform
- **Elasticsearch Integration**: Optional integration for retrieving logs from Elasticsearch clusters
- **Enriched Slack Notifications**: Lambda-powered notifications with:
  - Real-time crash alerts with recent container logs from CloudWatch, Coralogix, or Elasticsearch
  - Daily summary reports with crash patterns, affected services, and hourly distribution
  - Service health status and task definition details
  - Rich Slack formatting with blocks and attachments
  - Direct links to Coralogix or Elasticsearch/Kibana UI when applicable
- **Comprehensive Tagging**: Consistent resource tagging for better organization
- **IAM Security**: Least-privilege IAM roles and policies

## Usage

### Basic Usage (Logging Only)

```hcl
module "ecs_crash_monitor" {
  source = "./path/to/ecs-monitor"

  cluster_name = "my-ecs-cluster"
  environment  = "production"
}
```

### With Slack Notifications

```hcl
module "ecs_crash_monitor" {
  source = "./path/to/ecs-monitor"

  cluster_name                 = "my-ecs-cluster"
  environment                  = "production"
  enable_crash_notifier        = true
  slack_bot_token              = "xoxb-your-bot-token-here"
  crash_notifier_slack_channel = "#ecs-alerts"
  log_retention_days           = 14
}
```

### With Daily Summary Reports

```hcl
module "ecs_crash_monitor" {
  source = "./path/to/ecs-monitor"

  cluster_name          = "my-ecs-cluster"
  environment           = "production"
  enable_crash_notifier = true
  slack_bot_token       = "xoxb-your-bot-token-here"
  slack_channel         = "#ecs-alerts"
  enable_daily_summary  = true
  daily_summary_schedule = "cron(0 9 * * ? *)"  # 9 AM UTC daily
  log_retention_days    = 14
}
```

### With Elasticsearch Integration

```hcl
module "ecs_crash_monitor" {
  source = "./path/to/ecs-monitor"

  cluster_name                       = "my-ecs-cluster"
  environment                        = "production"
  enable_crash_notifier              = true
  slack_bot_token                    = "xoxb-your-bot-token-here"
  slack_channel                      = "#ecs-alerts"
  enable_elasticsearch_integration   = true
  elasticsearch_endpoint             = "https://elasticsearch.company.com"
  elasticsearch_username             = "elastic"
  elasticsearch_password             = "secure-password"
  elasticsearch_index_pattern        = "journey-logs-*"
  kibana_url                         = "https://kibana.company.com"
  log_retention_days                 = 14
}
```

### With Coralogix Integration

```hcl
module "ecs_crash_monitor" {
  source = "./path/to/ecs-monitor"

  cluster_name               = "my-ecs-cluster"
  environment                = "production"
  enable_crash_notifier      = true
  slack_bot_token            = "xoxb-your-bot-token-here"
  slack_channel                = "#ecs-alerts"
  enable_coralogix_integration = true
  coralogix_api_key            = "cxtp_your-coralogix-api-key"
  coralogix_region             = "eu2"
  coralogix_account            = "your-account-name"
  log_retention_days           = 14
}
```

### With VPC Configuration (Private Access)

```hcl
module "ecs_crash_monitor" {
  source = "./path/to/ecs-monitor"

  cluster_name                       = "my-ecs-cluster"
  environment                        = "production"
  enable_crash_notifier              = true
  slack_bot_token                    = "xoxb-your-bot-token-here"
  slack_channel                      = "#ecs-alerts"
  enable_elasticsearch_integration   = true
  elasticsearch_endpoint             = "https://elasticsearch.internal.vpc"
  elasticsearch_username             = "elastic"
  elasticsearch_password             = "secure-password"
  elasticsearch_index_pattern        = "journey-logs-*"
  kibana_url                         = "https://kibana.internal.vpc"
  
  # VPC Configuration for private access
  enable_vpc_config                  = true
  vpc_subnet_ids                     = ["subnet-12345678", "subnet-87654321"]
  vpc_security_group_ids             = ["sg-12345678"]
}
```

### Custom Lambda Function Name

```hcl
module "ecs_crash_monitor" {
  source = "./path/to/ecs-monitor"

  cluster_name          = "my-ecs-cluster"
  environment           = "production"
  enable_crash_notifier = true
  slack_bot_token       = "xoxb-your-bot-token-here"
  slack_channel         = "#ecs-alerts"
  crash_notifier_function_name = "custom-crash-notifier"
}
```

## Requirements

| Name | Version |
|------|---------|
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.0 |
| <a name="requirement_aws"></a> [aws](#requirement\_aws) | >= 5.0 |

## Providers

| Name | Version |
|------|---------|
| <a name="provider_aws"></a> [aws](#provider\_aws) | >= 5.0 |

## Resources

| Name | Type |
|------|------|
| [aws_cloudwatch_event_rule.ecs_task_state_changes](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_rule) | resource |
| [aws_cloudwatch_event_target.crash_logs_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_target) | resource |
| [aws_cloudwatch_event_target.crash_sns_target](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_event_target) | resource |
| [aws_cloudwatch_log_group.crash_events](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/cloudwatch_log_group) | resource |
| [aws_iam_role.eventbridge_logs_role](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role) | resource |
| [aws_iam_role_policy.eventbridge_logs_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/iam_role_policy) | resource |
| [aws_sns_topic.crash_notifications](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic) | resource |
| [aws_sns_topic_policy.crash_notifications_policy](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic_policy) | resource |
| [aws_sns_topic_subscription.crash_email_notification](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/sns_topic_subscription) | resource |

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| <a name="input_cluster_name"></a> [cluster\_name](#input\_cluster\_name) | The name of the ECS cluster | `string` | n/a | yes |
| <a name="input_coralogix_account"></a> [coralogix\_account](#input\_coralogix\_account) | Coralogix account name for generating UI links | `string` | `""` | no |
| <a name="input_coralogix_api_key"></a> [coralogix\_api\_key](#input\_coralogix\_api\_key) | Coralogix API key for log retrieval | `string` | `""` | no |
| <a name="input_coralogix_region"></a> [coralogix\_region](#input\_coralogix\_region) | Coralogix region (e.g., us, eu, eu2, ap, ap2) | `string` | `""` | no |
| <a name="input_daily_summary_function_name"></a> [daily\_summary\_function\_name](#input\_daily\_summary\_function\_name) | Name of the Lambda function for daily crash summaries | `string` | `""` | no |
| <a name="input_daily_summary_schedule"></a> [daily\_summary\_schedule](#input\_daily\_summary\_schedule) | Cron expression for daily summary schedule (default: 9 AM UTC daily) | `string` | `"cron(0 9 * * ? *)"` | no |
| <a name="input_elasticsearch_endpoint"></a> [elasticsearch\_endpoint](#input\_elasticsearch\_endpoint) | Elasticsearch endpoint URL (e.g., https://your-elasticsearch.com) | `string` | `""` | no |
| <a name="input_elasticsearch_index_pattern"></a> [elasticsearch\_index\_pattern](#input\_elasticsearch\_index\_pattern) | Elasticsearch index pattern for searching logs (e.g., 'journey-logs-*') | `string` | `""` | no |
| <a name="input_elasticsearch_password"></a> [elasticsearch\_password](#input\_elasticsearch\_password) | Elasticsearch password for authentication | `string` | `""` | no |
| <a name="input_elasticsearch_username"></a> [elasticsearch\_username](#input\_elasticsearch\_username) | Elasticsearch username for authentication | `string` | `""` | no |
| <a name="input_enable_coralogix_integration"></a> [enable\_coralogix\_integration](#input\_enable\_coralogix\_integration) | Whether to enable Coralogix integration for log retrieval | `bool` | `false` | no |
| <a name="input_enable_daily_summary"></a> [enable\_daily\_summary](#input\_enable\_daily\_summary) | Whether to enable daily crash summary reports | `bool` | `false` | no |
| <a name="input_enable_elasticsearch_integration"></a> [enable\_elasticsearch\_integration](#input\_enable\_elasticsearch\_integration) | Whether to enable Elasticsearch integration for log retrieval | `bool` | `false` | no |
| <a name="input_environment"></a> [environment](#input\_environment) | The environment for tagging purposes (e.g., dev, prod) | `string` | n/a | yes |
| <a name="input_kibana_url"></a> [kibana\_url](#input\_kibana\_url) | Kibana URL for generating UI links (e.g., 'https://kibana.company.com') | `string` | `""` | no |
| <a name="input_enable_crash_notifier"></a> [enable\_crash\_notifier](#input\_enable\_crash\_notifier) | Whether to enable crash notifier for Slack notifications | `bool` | `false` | no |
| <a name="input_enable_vpc_config"></a> [enable\_vpc\_config](#input\_enable\_vpc\_config) | Whether to deploy Lambda function within a VPC (required for private Elasticsearch/Coralogix access) | `bool` | `false` | no |
| <a name="input_crash_notifier_function_name"></a> [crash\_notifier\_function\_name](#input\_crash\_notifier\_function\_name) | Name of the Lambda function for crash notifications | `string` | `""` | no |
| <a name="input_log_retention_days"></a> [log\_retention\_days](#input\_log\_retention\_days) | Number of days to retain CloudWatch logs | `number` | `30` | no |
| <a name="input_slack_bot_token"></a> [slack\_bot\_token](#input\_slack\_bot\_token) | Slack bot token for sending crash notifications | `string` | `""` | no |
| <a name="input_slack_channel"></a> [slack\_channel](#input\_slack\_channel) | Slack channel ID or name for sending crash notifications | `string` | `""` | no |
| <a name="input_vpc_security_group_ids"></a> [vpc\_security\_group\_ids](#input\_vpc\_security\_group\_ids) | List of security group IDs for Lambda function (required if enable_vpc_config is true) | `list(string)` | `[]` | no |
| <a name="input_vpc_subnet_ids"></a> [vpc\_subnet\_ids](#input\_vpc\_subnet\_ids) | List of subnet IDs for Lambda function (required if enable_vpc_config is true) | `list(string)` | `[]` | no |

## Outputs

| Name | Description |
|------|-------------|
| <a name="output_daily_summary_lambda_arn"></a> [daily\_summary\_lambda\_arn](#output\_daily\_summary\_lambda\_arn) | ARN of the daily summary Lambda function (if enabled) |
| <a name="output_daily_summary_lambda_name"></a> [daily\_summary\_lambda\_name](#output\_daily\_summary\_lambda\_name) | Name of the daily summary Lambda function (if enabled) |
| <a name="output_daily_summary_schedule_rule_name"></a> [daily\_summary\_schedule\_rule\_name](#output\_daily\_summary\_schedule\_rule\_name) | Name of the EventBridge rule for daily summary schedule (if enabled) |
| <a name="output_eventbridge_rule_arn"></a> [eventbridge\_rule\_arn](#output\_eventbridge\_rule\_arn) | ARN of the EventBridge rule monitoring ECS task state changes |
| <a name="output_eventbridge_rule_name"></a> [eventbridge\_rule\_name](#output\_eventbridge\_rule\_name) | Name of the EventBridge rule monitoring ECS task state changes |
| <a name="output_iam_role_arn"></a> [iam\_role\_arn](#output\_iam\_role\_arn) | ARN of the IAM role used by EventBridge to write to CloudWatch Logs |
| <a name="output_crash_notifier_lambda_arn"></a> [crash\_notifier\_lambda\_arn](#output\_crash\_notifier\_lambda\_arn) | ARN of the crash notifier Lambda function (if enabled) |
| <a name="output_crash_notifier_lambda_name"></a> [crash\_notifier\_lambda\_name](#output\_crash\_notifier\_lambda\_name) | Name of the crash notifier Lambda function (if enabled) |
| <a name="output_log_group_arn"></a> [log\_group\_arn](#output\_log\_group\_arn) | ARN of the CloudWatch Log Group for crash events |
| <a name="output_log_group_name"></a> [log\_group\_name](#output\_log\_group\_name) | Name of the CloudWatch Log Group for crash events |

## How It Works

1. **EventBridge Rule**: Monitors ECS task state changes and filters for:
   - Tasks that have stopped
   - Tasks with non-zero exit codes
   - Tasks from services (not standalone tasks)

2. **CloudWatch Logs**: All crash events are logged to a dedicated log group with configurable retention

3. **Real-time Notifications** (Optional): When Slack notifications are enabled, crash events trigger a Lambda function that:
   - Extracts crash details from the EventBridge event
   - Enriches data by calling AWS APIs for:
     - Recent CloudWatch logs from the failed container
     - ECS service status and health
     - Task definition details
   - Formats and sends rich Slack notifications with blocks and attachments

4. **Daily Summary Reports** (Optional): When daily summaries are enabled, a scheduled Lambda function:
   - Runs daily at a configurable time (default: 9 AM UTC)
   - Analyzes all crash events from the previous day
   - Generates insights including:
     - Total crash count and affected services
     - Most common crash reasons and exit codes
     - Hourly distribution patterns
     - Top affected services and containers
   - Sends a comprehensive summary to Slack with trends and recommendations

## Slack Notification Features

The module provides two types of Slack notifications using the Slack Bot API:

### Real-time Crash Alerts

Immediate notifications for individual crash events including:

- **Header**: Clear crash alert with emoji
- **Key Details**: Cluster, service, exit code, and timestamp
- **Service Status**: Running/desired count and service health
- **Log Attachments**: Full container logs are attached as text files instead of embedded in the message
- **Task Information**: Task ID for debugging
- **Rich Formatting**: Uses Slack blocks for professional appearance

### Daily Summary Reports

Comprehensive daily analysis reports including:

- **Overview**: Total crashes and affected services summary
- **Key Insights**: Top crash reasons, most affected services, and common exit codes
- **Hourly Distribution**: When crashes occurred throughout the day (UTC)
- **Affected Services**: Complete list of services with crash counts
- **Trends**: Visual indicators for crash frequency and patterns
- **Zero-crash Celebrations**: Positive messaging when no crashes occurred

### Bot vs Webhook Advantages

The module uses Slack Bot API instead of webhooks to provide enhanced functionality:

- **File Attachments**: Logs are sent as downloadable text files, keeping the main message clean
- **Better Formatting**: Rich block formatting with proper threading
- **No Message Size Limits**: Large log outputs don't break notifications
- **Improved Readability**: Main alert is concise, detailed logs are in attachments

### Setup Requirements

To use Slack notifications, you'll need to:

1. Create a Slack app in your workspace
2. Add the `chat:write` and `files:write` scopes to your bot
3. Install the app to your workspace
4. Copy the Bot User OAuth Token (starts with `xoxb-`)
5. Invite the bot to your target channel
6. Use the channel name (e.g., `#ecs-alerts`) or channel ID

## Coralogix Integration

The module supports optional integration with Coralogix for log retrieval, providing enhanced log access and UI linking capabilities.

### Features

- **Automatic Log Detection**: Intelligently detects whether to use Coralogix or CloudWatch based on configuration
- **DataPrime Query API**: Uses Coralogix's query API to retrieve logs filtered by ECS task ARN
- **UI Link Generation**: Creates direct links to Coralogix UI with pre-filtered queries
- **Hybrid Support**: Falls back to CloudWatch if Coralogix is unavailable or not configured
- **Enhanced Notifications**: Slack messages include log source indicators and Coralogix UI links

### Configuration

Enable Coralogix integration by setting:

```hcl
enable_coralogix_integration = true
coralogix_api_key            = "cxtp_your-api-key"
coralogix_region             = "eu2"  # or us, eu, ap, ap2
coralogix_account            = "your-account-name"
```

### Requirements

1. **Coralogix API Key**: Create an API key with "Query" permissions in your Coralogix dashboard
2. **Log Format**: Your ECS tasks must send logs to Coralogix with the `ecs_task_arn` field included
3. **Task Configuration**: Logs can be sent via any method (Fluentd, Fluent Bit, etc.) as long as the task ARN is preserved

### How It Works

1. **Detection**: When enabled, the Lambda function first checks if Coralogix is available and configured
2. **Query**: Uses DataPrime API to query logs: `source logs last 1h | filter $d.ecs_task_arn ~ 'task-arn' | choose $d.message | limit 50`
3. **Fallback**: If no logs found in Coralogix, automatically tries CloudWatch
4. **UI Links**: Generates clickable links to Coralogix UI with pre-filtered queries

See the [Coralogix example](examples/with-coralogix/) for complete setup instructions.

## Elasticsearch Integration

The module supports optional integration with Elasticsearch for log retrieval, providing enhanced log access and UI linking capabilities.

### Features

- **Automatic Log Detection**: Intelligently detects whether to use Elasticsearch, Coralogix, or CloudWatch based on configuration
- **REST API Search**: Uses Elasticsearch Search API to retrieve logs filtered by ECS task ARN
- **Kibana UI Link Generation**: Creates direct links to Kibana with pre-filtered queries (when available)
- **Hybrid Support**: Falls back to CloudWatch if Elasticsearch is unavailable or not configured
- **Enhanced Notifications**: Slack messages include log source indicators and Elasticsearch/Kibana UI links

### Configuration

Enable Elasticsearch integration by setting:

```hcl
enable_elasticsearch_integration = true
elasticsearch_endpoint           = "https://elasticsearch.company.com"
elasticsearch_username           = "elastic"
elasticsearch_password           = "secure-password"
elasticsearch_index_pattern      = "journey-logs-*"
kibana_url                       = "https://kibana.company.com"
```

### Requirements

1. **Elasticsearch Cluster**: Accessible endpoint with authentication
2. **Log Format**: Your ECS tasks must send logs to Elasticsearch with the `ecs_task_arn` field included
3. **Index Structure**: Logs should be indexed with proper timestamp and message fields
4. **Network Access**: Lambda function must be able to reach Elasticsearch endpoint

### Example Log Document

```json
{
  "@timestamp": "2025-09-21T15:59:22.706Z",
  "message": "Application error occurred",
  "level": "error",
  "container_name": "app",
  "source": "stderr",
  "ecs_cluster": "production",
  "ecs_task_arn": "arn:aws:ecs:us-east-1:123456789012:task/production/abc123",
  "ecs_task_definition": "my-app:42",
  "appName": "my-application",
  "environment": "production"
}
```

### How It Works

1. **Detection**: When enabled, the Lambda function first checks if Elasticsearch is available and configured
2. **Query**: Uses Elasticsearch Search API with term query: `{"term": {"ecs_task_arn": {"value": "task-arn"}}}`
3. **Fallback**: If no logs found in Elasticsearch, automatically tries Coralogix or CloudWatch
4. **UI Links**: Generates clickable links to Kibana with pre-filtered queries

See the [Elasticsearch example](examples/with-elasticsearch/) for complete setup instructions.

## VPC Configuration

The module supports deploying the Lambda function within a VPC for accessing private resources like Elasticsearch clusters or Coralogix endpoints that are only available within your VPC.

### When to Use VPC Configuration

- **Private Elasticsearch**: When your Elasticsearch cluster is only accessible within your VPC
- **Private Coralogix**: When using private Coralogix endpoints or VPN connections
- **Network Security**: When your organization requires Lambda functions to run within specific network boundaries
- **Compliance**: When regulatory requirements mandate network isolation

### Configuration

Enable VPC configuration by setting:

```hcl
enable_vpc_config        = true
vpc_subnet_ids          = ["subnet-12345678", "subnet-87654321"]  # Private subnets
vpc_security_group_ids  = ["sg-12345678"]                        # Security group with appropriate access
```

### Requirements

1. **Private Subnets**: Use private subnets with NAT Gateway or VPC Endpoints for internet access
2. **Security Groups**: Configure security groups to allow:
   - Outbound HTTPS (443) to Elasticsearch/Coralogix endpoints
   - Outbound HTTPS (443) to Slack API (slack.com)
   - Outbound HTTPS (443) to AWS APIs (if not using VPC endpoints)
3. **NAT Gateway or VPC Endpoints**: Required for Lambda to access AWS services and external APIs
4. **DNS Resolution**: Ensure private DNS resolution is enabled in the VPC

### Security Group Example

```hcl
resource "aws_security_group" "lambda_sg" {
  name_prefix = "ecs-monitor-lambda-"
  vpc_id      = var.vpc_id

  egress {
    description = "HTTPS to Elasticsearch"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]  # Your VPC CIDR
  }

  egress {
    description = "HTTPS to internet (Slack, AWS APIs)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "ecs-monitor-lambda-sg"
  }
}
```

### Important Notes

- **Increased Cold Start**: VPC-enabled Lambda functions have slightly longer cold start times
- **ENI Limits**: Each Lambda execution creates ENIs; ensure sufficient ENI capacity
- **Timeout Considerations**: Network connectivity issues may require increased Lambda timeout
- **Cost Impact**: NAT Gateway usage will incur additional costs

### Troubleshooting VPC Issues

1. **Connection Timeouts**: Check security groups and NACLs
2. **DNS Resolution**: Verify VPC DNS settings and private hosted zones
3. **NAT Gateway**: Ensure NAT Gateway is properly configured for internet access
4. **ENI Limits**: Monitor ENI usage in your account and subnets

## Event Pattern

The module monitors events matching this pattern:

```json
{
  "source": ["aws.ecs"],
  "detail-type": ["ECS Task State Change"],
  "detail": {
    "clusterArn": ["arn:aws:ecs:region:account:cluster/cluster-name"],
    "stoppedReason": ["Essential container in task exited"],
    "containers": {
      "exitCode": [{"anything-but": [0]}]
    },
    "lastStatus": ["STOPPED"],
    "group": [{"prefix": "service:"}]
  }
}
```

## License

This module is released under the MIT License. See LICENSE for more information.
