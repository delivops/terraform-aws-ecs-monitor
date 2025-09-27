data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# CloudWatch Log Group for storing crash events
resource "aws_cloudwatch_log_group" "crash_events" {
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
      "stoppedReason": [
        # Health check failures
        "Task failed container health checks",
        "Task failed ELB health checks",
        { "prefix": "Task failed to pass" },
        
        # Official AWS ECS error categories
        { "prefix": "TaskFailedToStart" },
        { "prefix": "ResourceInitializationError" },
        { "prefix": "ResourceNotFoundException" },
        { "prefix": "SpotInterruptionError" },
        { "prefix": "InternalError" },
        { "prefix": "OutOfMemoryError" },
        { "prefix": "ContainerRuntimeError" },
        { "prefix": "ContainerRuntimeTimeoutError" },
        { "prefix": "CannotStartContainerError" },
        { "prefix": "CannotStopContainerError" },
        { "prefix": "CannotInspectContainerError" },
        { "prefix": "CannotCreateVolumeError" },
        { "prefix": "CannotPullContainer" },
        
        # Additional common error patterns
        { "prefix": "Task failed" },
        { "prefix": "Essential container in task exited" },
        { "prefix": "HostEC2" },
        { "prefix": "Container runtime" }
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
  rule      = aws_cloudwatch_event_rule.ecs_task_state_changes.name
  target_id = "CrashLogsTarget"
  arn       = aws_cloudwatch_log_group.crash_events.arn
}

# Resource policy for CloudWatch Log Group to allow EventBridge
resource "aws_cloudwatch_log_resource_policy" "crash_events_policy" {
  policy_name     = "${var.cluster_name}-crash-events-policy"
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
        Resource = "${aws_cloudwatch_log_group.crash_events.arn}:*"
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_event_rule.ecs_task_state_changes.arn
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
    SLACK_BOT_TOKEN                    = var.slack_bot_token
    SLACK_CHANNEL                      = var.crash_notifier_slack_channel
    CLUSTER_NAME                       = var.cluster_name
    ENABLE_CORALOGIX_INTEGRATION       = var.enable_coralogix_integration
    CORALOGIX_API_KEY                  = var.coralogix_api_key
    CORALOGIX_REGION                   = var.coralogix_region
    CORALOGIX_ACCOUNT                  = var.coralogix_account
    ENABLE_ELASTICSEARCH_INTEGRATION   = var.enable_elasticsearch_integration
    ELASTICSEARCH_ENDPOINT             = var.elasticsearch_endpoint
    ELASTICSEARCH_USERNAME             = var.elasticsearch_username
    ELASTICSEARCH_PASSWORD             = var.elasticsearch_password
    ELASTICSEARCH_INDEX_PATTERN        = var.elasticsearch_index_pattern
    KIBANA_URL                         = var.kibana_url
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
    }
  }

  tags = {
    Name        = var.crash_notifier_function_name != "" ? var.crash_notifier_function_name : "${var.cluster_name}-crash-notifier"
    Environment = var.environment
    Purpose     = "ECS crash event processing and Slack notifications"
  }
}

# EventBridge Target for Crash Notifier Lambda
resource "aws_cloudwatch_event_target" "crash_notifier_target" {
  count     = var.enable_crash_notifier ? 1 : 0
  rule      = aws_cloudwatch_event_rule.ecs_task_state_changes.name
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
  source_arn    = aws_cloudwatch_event_rule.ecs_task_state_changes.arn
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
  timeout       = 300  # 5 minutes to process potentially large log volumes

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
