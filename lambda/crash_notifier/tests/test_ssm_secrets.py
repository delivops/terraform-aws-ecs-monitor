"""
Tests for loading secrets from SSM Parameter Store.

Run from lambda/crash_notifier/ with:
    python -m unittest tests.test_ssm_secrets -v
"""

import os
import sys
import unittest
from unittest.mock import patch

import boto3
from moto import mock_aws

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAMBDA_DIR = os.path.dirname(_HERE)
if _LAMBDA_DIR not in sys.path:
    sys.path.insert(0, _LAMBDA_DIR)

from ssm_secrets import load_ssm_secrets  # noqa: E402

AWS_ENV = {
    "AWS_DEFAULT_REGION": "us-east-1",
    "AWS_ACCESS_KEY_ID": "testing",
    "AWS_SECRET_ACCESS_KEY": "testing",
    "AWS_SESSION_TOKEN": "testing",
}


@mock_aws
class LoadSsmSecretsTest(unittest.TestCase):
    def setUp(self):
        self.ssm = boto3.client("ssm", region_name="us-east-1")
        self.ssm.put_parameter(Name="/ecs-monitor/slack", Value="xoxb-from-ssm", Type="SecureString")

    def test_sets_variable_from_parameter(self):
        with patch.dict(os.environ, {**AWS_ENV, "SLACK_BOT_TOKEN_SSM_PARAMETER": "/ecs-monitor/slack"}, clear=True):
            load_ssm_secrets()
            self.assertEqual(os.environ["SLACK_BOT_TOKEN"], "xoxb-from-ssm")

    def test_keeps_a_value_already_set(self):
        env = {**AWS_ENV, "SLACK_BOT_TOKEN_SSM_PARAMETER": "/ecs-monitor/slack", "SLACK_BOT_TOKEN": "xoxb-plain"}
        with patch.dict(os.environ, env, clear=True):
            load_ssm_secrets()
            self.assertEqual(os.environ["SLACK_BOT_TOKEN"], "xoxb-plain")

    def test_nothing_to_do_without_parameters(self):
        with patch.dict(os.environ, {**AWS_ENV, "SLACK_BOT_TOKEN": "xoxb-plain"}, clear=True):
            with patch("ssm_secrets.boto3.client") as client:
                load_ssm_secrets()
                client.assert_not_called()

    def test_missing_parameter_raises(self):
        with patch.dict(os.environ, {**AWS_ENV, "CORALOGIX_API_KEY_SSM_PARAMETER": "/missing"}, clear=True):
            with self.assertRaises(Exception):
                load_ssm_secrets()
            self.assertNotIn("CORALOGIX_API_KEY", os.environ)


if __name__ == "__main__":
    unittest.main()
