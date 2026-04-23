data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

locals {
  enable_crash_monitoring = var.enable_crash_notifier || var.enable_daily_summary
}

# CloudWatch Log Group for storing crash events
resource "aws_cloudwatch_log_group" "crash_events" {
  count             = local.enable_crash_monitoring ? 1 : 0
  name              = "/aws/ecs/monitoring/${var.cluster_name}/crash-events"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.cluster_name}-crash-events"
    Environment = var.environment
    Purpose     = "ECS crash event logging"
  }
}

# EventBridge Rule for ECS task state changes
resource "aws_cloudwatch_event_rule" "ecs_task_state_changes" {
  count       = local.enable_crash_monitoring ? 1 : 0
  name        = "${var.cluster_name}-ecs-task-state-changes"
  description = "Capture ECS task state changes for monitoring"

  event_pattern = jsonencode({
    source      = ["aws.ecs"]
    detail-type = ["ECS Task State Change"]
    detail = {
      clusterArn = ["arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cluster/${var.cluster_name}"]
      lastStatus = ["STOPPED"]
      group = [{
        prefix = "service:"
      }]
      # Match all official ECS error categories from AWS documentation
      "stoppedReason" : [
        # Health check failures
        "Task failed container health checks",
        "Task failed ELB health checks",
        { "prefix" : "Task failed to pass" },

        # Official AWS ECS error categories
        { "prefix" : "TaskFailedToStart" },
        { "prefix" : "ResourceInitializationError" },
        { "prefix" : "ResourceNotFoundException" },
        { "prefix" : "SpotInterruptionError" },
        { "prefix" : "InternalError" },
        { "prefix" : "OutOfMemoryError" },
        { "prefix" : "ContainerRuntimeError" },
        { "prefix" : "ContainerRuntimeTimeoutError" },
        { "prefix" : "CannotStartContainerError" },
        { "prefix" : "CannotStopContainerError" },
        { "prefix" : "CannotInspectContainerError" },
        { "prefix" : "CannotCreateVolumeError" },
        { "prefix" : "CannotPullContainer" },

        # Additional common error patterns
        { "prefix" : "Task failed" },
        { "prefix" : "Essential container in task exited" },
        { "prefix" : "HostEC2" },
        { "prefix" : "Container runtime" }
      ]
    }
  })

  tags = {
    Name        = "${var.cluster_name}-ecs-task-state-changes"
    Environment = var.environment
    Purpose     = "Monitor ECS task failures"
  }
}

# EventBridge Target for direct CloudWatch Logs
resource "aws_cloudwatch_event_target" "crash_logs_target" {
  count     = local.enable_crash_monitoring ? 1 : 0
  rule      = aws_cloudwatch_event_rule.ecs_task_state_changes[0].name
  target_id = "CrashLogsTarget"
  arn       = aws_cloudwatch_log_group.crash_events[0].arn
}

# Resource policy for CloudWatch Log Group to allow EventBridge
resource "aws_cloudwatch_log_resource_policy" "crash_events_policy" {
  count       = local.enable_crash_monitoring ? 1 : 0
  policy_name = "${var.cluster_name}-crash-events-policy"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
        Action = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "${aws_cloudwatch_log_group.crash_events[0].arn}:*"
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_event_rule.ecs_task_state_changes[0].arn
          }
        }
      }
    ]
  })
}

# Lambda function for enriched Slack notifications using terraform-aws-modules/lambda/aws
module "crash_notifier_lambda" {
  count = var.enable_crash_notifier ? 1 : 0

  source  = "terraform-aws-modules/lambda/aws"
  version = "7.21.1"

  function_name = var.crash_notifier_function_name != "" ? var.crash_notifier_function_name : "${var.cluster_name}-crash-notifier"
  description   = "ECS crash event processing and Slack notifications"
  handler       = "crash_notifier.lambda_handler"
  runtime       = "python3.12"
  timeout       = 60

  source_path = "${path.module}/lambda/crash_notifier"

  # VPC Configuration (optional)
  vpc_subnet_ids         = var.enable_vpc_config ? var.vpc_subnet_ids : null
  vpc_security_group_ids = var.enable_vpc_config ? var.vpc_security_group_ids : null

  environment_variables = {
    SLACK_BOT_TOKEN                  = var.slack_bot_token
    SLACK_CHANNEL                    = var.crash_notifier_slack_channel
    CLUSTER_NAME                     = var.cluster_name
    ENABLE_CORALOGIX_INTEGRATION     = var.enable_coralogix_integration
    CORALOGIX_API_KEY                = var.coralogix_api_key
    CORALOGIX_REGION                 = var.coralogix_region
    CORALOGIX_ACCOUNT                = var.coralogix_account
    ENABLE_ELASTICSEARCH_INTEGRATION = var.enable_elasticsearch_integration
    ELASTICSEARCH_ENDPOINT           = var.elasticsearch_endpoint
    ELASTICSEARCH_USERNAME           = var.elasticsearch_username
    ELASTICSEARCH_PASSWORD           = var.elasticsearch_password
    ELASTICSEARCH_INDEX_PATTERN      = var.elasticsearch_index_pattern
    KIBANA_URL                       = var.kibana_url
    ALERT_STATE_TABLE                = aws_dynamodb_table.crash_alert_state[0].name
    AGGREGATION_WINDOW_MINUTES       = tostring(var.crash_alert_aggregation_window_minutes)
    CRASH_ALERT_MODE                 = var.crash_alert_mode
  }

  cloudwatch_logs_retention_in_days = var.log_retention_days

  attach_policy_statements = true
  policy_statements = {
    logs = {
      effect = "Allow",
      actions = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents"
      ],
      resources = [
        "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
      ]
    },
    ecs = {
      effect = "Allow",
      actions = [
        "ecs:DescribeServices",
        "ecs:DescribeTaskDefinition",
        "ecs:DescribeTasks"
      ],
      resources = ["*"]
    },
    vpc = {
      effect = "Allow",
      actions = [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface",
        "ec2:AttachNetworkInterface",
        "ec2:DetachNetworkInterface"
      ],
      resources = ["*"]
    },
    dynamodb = {
      effect = "Allow",
      actions = [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:PutItem",
        "dynamodb:DeleteItem"
      ],
      resources = [
        aws_dynamodb_table.crash_alert_state[0].arn
      ]
    }
  }

  trigger_on_package_timestamp = false

  tags = {
    Name        = var.crash_notifier_function_name != "" ? var.crash_notifier_function_name : "${var.cluster_name}-crash-notifier"
    Environment = var.environment
    Purpose     = "ECS crash event processing and Slack notifications"
  }
}

# DynamoDB table for crash alert aggregation state (deduplicates repeat crashes within a window)
resource "aws_dynamodb_table" "crash_alert_state" {
  count = var.enable_crash_notifier ? 1 : 0

  name         = "${var.cluster_name}-crash-alert-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "service_key"

  attribute {
    name = "service_key"
    type = "S"
  }

  ttl {
    attribute_name = "window_expires_at"
    enabled        = true
  }

  tags = {
    Name        = "${var.cluster_name}-crash-alert-state"
    Environment = var.environment
    Purpose     = "Aggregate ECS crash-loop Slack alerts within a sliding window"
  }
}

# EventBridge Target for Crash Notifier Lambda
resource "aws_cloudwatch_event_target" "crash_notifier_target" {
  count     = var.enable_crash_notifier ? 1 : 0
  rule      = aws_cloudwatch_event_rule.ecs_task_state_changes[0].name
  target_id = "CrashNotifierTarget"
  arn       = module.crash_notifier_lambda[0].lambda_function_arn
}

# Lambda permission for EventBridge to invoke crash notifier function
resource "aws_lambda_permission" "allow_eventbridge_crash_notifier" {
  count         = var.enable_crash_notifier ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = module.crash_notifier_lambda[0].lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.ecs_task_state_changes[0].arn
}

# Daily Summary Lambda Function
module "daily_summary_lambda" {
  count = var.enable_daily_summary ? 1 : 0

  source  = "terraform-aws-modules/lambda/aws"
  version = "7.21.1"

  function_name = var.daily_summary_function_name != "" ? var.daily_summary_function_name : "${var.cluster_name}-daily-summary"
  description   = "Daily ECS crash summary analysis and Slack notifications"
  handler       = "daily_summary.lambda_handler"
  runtime       = "python3.12"
  timeout       = 300 # 5 minutes to process potentially large log volumes

  source_path = "${path.module}/lambda/daily_summary"

  # VPC Configuration (optional)
  vpc_subnet_ids         = var.enable_vpc_config ? var.vpc_subnet_ids : null
  vpc_security_group_ids = var.enable_vpc_config ? var.vpc_security_group_ids : null

  environment_variables = {
    SLACK_BOT_TOKEN = var.slack_bot_token
    SLACK_CHANNEL   = var.daily_summary_slack_channel != "" ? var.daily_summary_slack_channel : var.crash_notifier_slack_channel
    CLUSTER_NAME    = var.cluster_name
  }

  cloudwatch_logs_retention_in_days = var.log_retention_days

  attach_policy_statements = true
  policy_statements = {
    logs = {
      effect = "Allow",
      actions = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:FilterLogEvents"
      ],
      resources = [
        "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
      ]
    }
  }

  tags = {
    Name        = var.daily_summary_function_name != "" ? var.daily_summary_function_name : "${var.cluster_name}-daily-summary"
    Environment = var.environment
    Purpose     = "Daily ECS crash summary analysis and Slack notifications"
  }
}

# EventBridge Rule for daily summary (scheduled every day at 9 AM UTC)
resource "aws_cloudwatch_event_rule" "daily_summary_schedule" {
  count               = var.enable_daily_summary ? 1 : 0
  name                = "${var.cluster_name}-daily-summary-schedule"
  description         = "Trigger daily ECS crash summary"
  schedule_expression = var.daily_summary_schedule

  tags = {
    Name        = "${var.cluster_name}-daily-summary-schedule"
    Environment = var.environment
    Purpose     = "Schedule daily crash summary"
  }
}

# EventBridge Target for Daily Summary Lambda
resource "aws_cloudwatch_event_target" "daily_summary_target" {
  count     = var.enable_daily_summary ? 1 : 0
  rule      = aws_cloudwatch_event_rule.daily_summary_schedule[0].name
  target_id = "DailySummaryTarget"
  arn       = module.daily_summary_lambda[0].lambda_function_arn
}

# Lambda permission for EventBridge to invoke daily summary function
resource "aws_lambda_permission" "allow_eventbridge_daily_summary" {
  count         = var.enable_daily_summary ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridgeSchedule"
  action        = "lambda:InvokeFunction"
  function_name = module.daily_summary_lambda[0].lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_summary_schedule[0].arn
}

# ============================================================================
# Logs Anomalies Lambda Function
# ============================================================================

# DynamoDB table for tracking anomaly notification state
resource "aws_dynamodb_table" "logs_anomalies_state" {
  count = var.enable_logs_anomalies ? 1 : 0

  name         = var.logs_anomalies_dynamodb_table_name != "" ? var.logs_anomalies_dynamodb_table_name : "${var.cluster_name}-logs-anomalies-state"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "anomaly_hash"

  attribute {
    name = "anomaly_hash"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  tags = {
    Name        = var.logs_anomalies_dynamodb_table_name != "" ? var.logs_anomalies_dynamodb_table_name : "${var.cluster_name}-logs-anomalies-state"
    Environment = var.environment
    Purpose     = "Track log anomaly notifications to prevent duplicates"
  }
}

# Local value to compute the log group prefixes list
locals {
  logs_anomalies_primary_prefix = var.logs_anomalies_log_group_prefix != "" ? var.logs_anomalies_log_group_prefix : "/ecs/${var.cluster_name}"
  logs_anomalies_all_prefixes   = concat([local.logs_anomalies_primary_prefix], var.logs_anomalies_additional_log_groups)
}

# Lambda function for log anomaly detection and notifications
module "logs_anomalies_lambda" {
  count = var.enable_logs_anomalies ? 1 : 0

  source  = "terraform-aws-modules/lambda/aws"
  version = "7.21.1"

  function_name = var.logs_anomalies_function_name != "" ? var.logs_anomalies_function_name : "${var.cluster_name}-logs-anomalies"
  description   = "CloudWatch Logs anomaly detection and Slack notifications"
  handler       = "logs_anomalies.handler"
  runtime       = "python3.12"
  timeout       = 120

  source_path = "${path.module}/lambda/logs_anomalies"

  # VPC Configuration (optional)
  vpc_subnet_ids         = var.enable_vpc_config ? var.vpc_subnet_ids : null
  vpc_security_group_ids = var.enable_vpc_config ? var.vpc_security_group_ids : null

  environment_variables = {
    LOG_GROUP_PREFIXES = jsonencode(local.logs_anomalies_all_prefixes)
    DYNAMODB_TABLE     = aws_dynamodb_table.logs_anomalies_state[0].name
    SLACK_BOT_TOKEN    = var.slack_bot_token
    SLACK_CHANNEL      = var.logs_anomalies_slack_channel
    PRIORITY_FILTER    = var.logs_anomalies_priority_filter
    TTL_DAYS           = tostring(var.logs_anomalies_ttl_days)
  }

  cloudwatch_logs_retention_in_days = var.log_retention_days

  attach_policy_statements = true
  policy_statements = {
    logs = {
      effect = "Allow",
      actions = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogGroups",
        "logs:ListLogAnomalyDetectors",
        "logs:ListAnomalies"
      ],
      resources = [
        "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:*"
      ]
    },
    dynamodb = {
      effect = "Allow",
      actions = [
        "dynamodb:GetItem",
        "dynamodb:PutItem"
      ],
      resources = [
        aws_dynamodb_table.logs_anomalies_state[0].arn
      ]
    },
    vpc = {
      effect = "Allow",
      actions = [
        "ec2:CreateNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DeleteNetworkInterface",
        "ec2:AttachNetworkInterface",
        "ec2:DetachNetworkInterface"
      ],
      resources = ["*"]
    }
  }

  trigger_on_package_timestamp = false

  tags = {
    Name        = var.logs_anomalies_function_name != "" ? var.logs_anomalies_function_name : "${var.cluster_name}-logs-anomalies"
    Environment = var.environment
    Purpose     = "CloudWatch Logs anomaly detection and Slack notifications"
  }
}

# EventBridge Rule for logs anomalies schedule
resource "aws_cloudwatch_event_rule" "logs_anomalies_schedule" {
  count               = var.enable_logs_anomalies ? 1 : 0
  name                = "${var.cluster_name}-logs-anomalies-schedule"
  description         = "Trigger log anomaly detection checks"
  schedule_expression = var.logs_anomalies_schedule

  tags = {
    Name        = "${var.cluster_name}-logs-anomalies-schedule"
    Environment = var.environment
    Purpose     = "Schedule log anomaly detection"
  }
}

# EventBridge Target for Logs Anomalies Lambda
resource "aws_cloudwatch_event_target" "logs_anomalies_target" {
  count     = var.enable_logs_anomalies ? 1 : 0
  rule      = aws_cloudwatch_event_rule.logs_anomalies_schedule[0].name
  target_id = "LogsAnomaliesTarget"
  arn       = module.logs_anomalies_lambda[0].lambda_function_arn
}

# Lambda permission for EventBridge to invoke logs anomalies function
resource "aws_lambda_permission" "allow_eventbridge_logs_anomalies" {
  count         = var.enable_logs_anomalies ? 1 : 0
  statement_id  = "AllowExecutionFromEventBridgeSchedule"
  action        = "lambda:InvokeFunction"
  function_name = module.logs_anomalies_lambda[0].lambda_function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.logs_anomalies_schedule[0].arn
}
