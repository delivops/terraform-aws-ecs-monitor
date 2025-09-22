# ECS Crash Monitor with Elasticsearch Integration

This example demonstrates how to set up the ECS Crash Monitor with Elasticsearch integration for enhanced log retrieval and analysis.

## Overview

This configuration enables:
- ECS task crash monitoring and notifications
- Slack notifications for crash events
- Elasticsearch integration for log retrieval
- Kibana UI links in Slack notifications (if available)

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **ECS Cluster** running your applications
3. **Elasticsearch Cluster** with:
   - HTTP/HTTPS endpoint accessible from Lambda
   - Authentication credentials
   - Logs indexed with `ecs_task_arn` field
4. **Slack Bot** with appropriate permissions

## Elasticsearch Requirements

Your Elasticsearch cluster should have logs indexed with the following fields:
- `ecs_task_arn`: The ECS task ARN for filtering
- `@timestamp`: Timestamp for sorting
- `message`: Log message content
- `level`: Log level (info, error, etc.)
- `container_name`: Container name
- `source`: Log source (stdout/stderr)

Example log document structure:
```json
{
  "@timestamp": "2025-09-21T15:59:22.706Z",
  "message": "Application error occurred",
  "level": "error",
  "container_name": "app",
  "source": "stderr",
  "ecs_cluster": "production",
  "ecs_task_arn": "arn:aws:ecs:us-east-1:123456789012:task/production/abc123...",
  "ecs_task_definition": "my-app:42",
  "appName": "my-application",
  "environment": "production"
}
```

## Configuration

1. **Copy the example variables file:**
   ```bash
   cp terraform.tfvars.example terraform.tfvars
   ```

2. **Edit terraform.tfvars with your values:**
   ```hcl
   aws_region   = "us-east-1"
   cluster_name = "my-production-cluster"
   environment  = "production"
   
   # Slack configuration
   slack_bot_token = "xoxb-your-bot-token"
   slack_channel   = "#production-alerts"
   
   # Elasticsearch configuration
   elasticsearch_endpoint      = "https://elasticsearch.mycompany.com"
   elasticsearch_username      = "elastic"
   elasticsearch_password      = "secure-password"
   elasticsearch_index_pattern = "application-logs-*"
   kibana_url                  = "https://kibana.mycompany.com"
   
   # VPC Configuration (if Elasticsearch is private)
   enable_vpc_config        = true
   vpc_subnet_ids          = ["subnet-12345678", "subnet-87654321"]
   vpc_security_group_ids  = ["sg-12345678"]
   ```

## Deployment

1. **Initialize Terraform:**
   ```bash
   terraform init
   ```

2. **Plan the deployment:**
   ```bash
   terraform plan
   ```

3. **Apply the configuration:**
   ```bash
   terraform apply
   ```

## Features

### Enhanced Slack Notifications
- Rich formatted crash notifications
- Direct links to Elasticsearch/Kibana for log analysis
- Container-specific crash details
- Task and service information

### Elasticsearch Integration
- Automatic log retrieval based on task ARN
- Support for custom index patterns
- Fallback to CloudWatch if Elasticsearch unavailable
- Kibana UI link generation (when available)

### Security
- Sensitive values marked as sensitive
- Environment variables encrypted in Lambda
- Basic authentication for Elasticsearch

## Testing

To test the integration:

1. **Trigger a test crash** in your ECS service
2. **Check CloudWatch Logs** for the crash event
3. **Verify Slack notification** with Elasticsearch logs
4. **Test Kibana link** (if applicable)

## Troubleshooting

### Common Issues

1. **No logs retrieved from Elasticsearch:**
   - Verify endpoint URL and credentials
   - Check index pattern matches your log indices
   - Ensure logs contain `ecs_task_arn` field

2. **Kibana links not working:**
   - Verify Kibana is accessible at expected URL
   - Check index pattern in Kibana matches configuration
   - Ensure proper authentication for Kibana access

3. **Lambda timeout errors:**
   - Increase Lambda timeout if Elasticsearch queries are slow
   - Check network connectivity from Lambda to Elasticsearch

### Logs and Debugging

Check Lambda logs in CloudWatch:
```bash
aws logs tail /aws/lambda/your-function-name --follow
```

## Next Steps

- Configure alerting rules in Elasticsearch/Kibana
- Set up dashboards for crash analysis
- Configure index lifecycle management
- Consider adding additional log fields for enhanced filtering