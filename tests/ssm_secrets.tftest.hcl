# Plan-only tests with mocked providers: no AWS account and no Lambda build needed.
# Run with: terraform init -backend=false && terraform test

mock_provider "external" {}

mock_provider "local" {}

mock_provider "null" {}

mock_provider "aws" {
  mock_data "aws_region" {
    defaults = { name = "us-east-1", region = "us-east-1" }
  }
  mock_data "aws_caller_identity" {
    defaults = { account_id = "123456789012" }
  }
  mock_data "aws_partition" {
    defaults = { partition = "aws" }
  }
  mock_data "aws_iam_policy_document" {
    defaults = { json = "{}" }
  }
}

override_data {
  target = module.crash_notifier_lambda[0].data.external.archive_prepare[0]
  values = {
    result = {
      filename            = "builds/mock.zip"
      build_plan          = "{}"
      build_plan_filename = "builds/mock.plan.json"
      timestamp           = "0"
      was_missing         = "false"
    }
  }
}

override_data {
  target = module.daily_summary_lambda[0].data.external.archive_prepare[0]
  values = {
    result = {
      filename            = "builds/mock.zip"
      build_plan          = "{}"
      build_plan_filename = "builds/mock.plan.json"
      timestamp           = "0"
      was_missing         = "false"
    }
  }
}

override_data {
  target = module.logs_anomalies_lambda[0].data.external.archive_prepare[0]
  values = {
    result = {
      filename            = "builds/mock.zip"
      build_plan          = "{}"
      build_plan_filename = "builds/mock.plan.json"
      timestamp           = "0"
      was_missing         = "false"
    }
  }
}

variables {
  cluster_name          = "test"
  environment           = "test"
  enable_crash_notifier = true
  enable_daily_summary  = true
  enable_logs_anomalies = true
}

run "plain_token_stays_backward_compatible" {
  command = plan

  variables {
    slack_bot_token   = "xoxb-plain"
    coralogix_api_key = "cx-plain"
  }

  assert {
    condition     = local.slack_secret_env == tomap({ SLACK_BOT_TOKEN = "xoxb-plain" })
    error_message = "without an SSM parameter the token is passed as before"
  }
  assert {
    condition     = local.coralogix_secret_env == tomap({ CORALOGIX_API_KEY = "cx-plain" })
    error_message = "without an SSM parameter the Coralogix key is passed as before"
  }
  assert {
    condition     = length(local.crash_notifier_ssm_policy_statements) == 0 && length(local.slack_ssm_policy_statements) == 0
    error_message = "no SSM permission is added when no parameter is given"
  }
}

run "ssm_parameters_replace_plain_values" {
  command = plan

  variables {
    slack_bot_token                      = "ignored"
    slack_bot_token_ssm_parameter        = "/ecs-monitor/slack-bot-token"
    elasticsearch_password_ssm_parameter = "es-password"
  }

  assert {
    condition     = local.slack_secret_env == tomap({ SLACK_BOT_TOKEN_SSM_PARAMETER = "/ecs-monitor/slack-bot-token" })
    error_message = "the plain token must not reach the environment when a parameter is given"
  }
  assert {
    condition     = local.elasticsearch_secret_env == tomap({ ELASTICSEARCH_PASSWORD_SSM_PARAMETER = "es-password" })
    error_message = "the Elasticsearch password comes from its parameter"
  }
  assert {
    condition = toset(local.crash_notifier_ssm_policy_statements.ssm_secrets.resources) == toset([
      "arn:aws:ssm:us-east-1:123456789012:parameter/ecs-monitor/slack-bot-token",
      "arn:aws:ssm:us-east-1:123456789012:parameter/es-password",
    ])
    error_message = "the crash notifier may read exactly its parameters"
  }
  assert {
    condition     = toset(local.slack_ssm_policy_statements.ssm_secrets.resources) == toset(["arn:aws:ssm:us-east-1:123456789012:parameter/ecs-monitor/slack-bot-token"])
    error_message = "the other Lambdas may read only the Slack parameter"
  }
  assert {
    condition     = !contains(keys(local.crash_notifier_ssm_policy_statements), "ssm_secrets_kms")
    error_message = "no KMS statement without a customer managed key"
  }
}

run "customer_managed_key" {
  command = plan

  variables {
    slack_bot_token_ssm_parameter = "/x"
    ssm_parameters_kms_key_arn    = "arn:aws:kms:us-east-1:123456789012:key/abc"
  }

  assert {
    condition     = toset(local.slack_ssm_policy_statements.ssm_secrets_kms.resources) == toset(["arn:aws:kms:us-east-1:123456789012:key/abc"])
    error_message = "kms:Decrypt is granted on the given key"
  }
}
