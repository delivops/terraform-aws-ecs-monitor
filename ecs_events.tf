# ============================================================================
# ECS Events — Capture all ECS events to CloudWatch Logs
# ============================================================================

# CloudWatch Log Group for storing all ECS events
resource "aws_cloudwatch_log_group" "ecs_events" {
  count             = var.enable_ecs_events ? 1 : 0
  name              = "/aws/ecs/monitoring/${var.cluster_name}/ecs-events"
  retention_in_days = coalesce(var.ecs_events_log_retention_days, var.log_retention_days)

  tags = {
    Name        = "${var.cluster_name}-ecs-events"
    Environment = var.environment
    Purpose     = "ECS all-events logging"
  }
}

# EventBridge Rule — capture all ECS events for the cluster
resource "aws_cloudwatch_event_rule" "ecs_all_events" {
  count       = var.enable_ecs_events ? 1 : 0
  name        = "${var.cluster_name}-ecs-all-events"
  description = "Capture all ECS events for cluster: ${var.cluster_name}"

  event_pattern = jsonencode({
    source      = ["aws.ecs"]
    detail-type = var.ecs_events_detail_types
    detail = {
      clusterArn = ["arn:aws:ecs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:cluster/${var.cluster_name}"]
    }
  })

  tags = {
    Name        = "${var.cluster_name}-ecs-all-events"
    Environment = var.environment
    Purpose     = "Capture all ECS events"
  }
}

# EventBridge Target — route all ECS events to the log group
resource "aws_cloudwatch_event_target" "ecs_events_to_cw_logs" {
  count     = var.enable_ecs_events ? 1 : 0
  rule      = aws_cloudwatch_event_rule.ecs_all_events[0].name
  target_id = "EcsEventsToCloudWatch"
  arn       = aws_cloudwatch_log_group.ecs_events[0].arn
}

# Resource policy — allow EventBridge to write to the ECS events log group
resource "aws_cloudwatch_log_resource_policy" "ecs_events_policy" {
  count       = var.enable_ecs_events ? 1 : 0
  policy_name = "${var.cluster_name}-ecs-events-policy"
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
        Resource = "${aws_cloudwatch_log_group.ecs_events[0].arn}:*"
        Condition = {
          ArnEquals = {
            "aws:SourceArn" = aws_cloudwatch_event_rule.ecs_all_events[0].arn
          }
        }
      }
    ]
  })
}
