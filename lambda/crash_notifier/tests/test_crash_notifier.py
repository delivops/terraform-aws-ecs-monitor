"""
Tests for the crash_notifier aggregation/deduplication logic.

Run from lambda/crash_notifier/ with:
    python -m unittest tests.test_crash_notifier -v
"""

import importlib
import json
import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import boto3
from moto import mock_aws


# Ensure the parent lambda directory is importable (flat-module layout).
_HERE = os.path.dirname(os.path.abspath(__file__))
_LAMBDA_DIR = os.path.dirname(_HERE)
if _LAMBDA_DIR not in sys.path:
    sys.path.insert(0, _LAMBDA_DIR)


TABLE_NAME = "test-crash-alert-state"
TEST_CHANNEL = "C_TEST"


def _base_env():
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"
    os.environ["AWS_REGION"] = "us-east-1"
    os.environ["ALERT_STATE_TABLE"] = TABLE_NAME
    os.environ["AGGREGATION_WINDOW_MINUTES"] = "30"
    os.environ["CRASH_ALERT_MODE"] = "edit_and_thread"
    os.environ["SLACK_BOT_TOKEN"] = "xoxb-test"
    os.environ["SLACK_CHANNEL"] = TEST_CHANNEL
    os.environ["CLUSTER_NAME"] = "test-cluster"


def _sample_event(task_id="t1", exit_code=1, reason="oom"):
    return {
        "detail": {
            "clusterArn": "arn:aws:ecs:us-east-1:123456789012:cluster/test-cluster",
            "group": "service:my-service",
            "taskArn": f"arn:aws:ecs:us-east-1:123456789012:task/test-cluster/{task_id}",
            "taskDefinitionArn": "arn:aws:ecs:us-east-1:123456789012:task-definition/my-service:42",
            "startedAt": "2026-04-23T10:00:00Z",
            "createdAt": "2026-04-23T10:00:00Z",
            "stoppedReason": reason,
            "stopCode": "EssentialContainerExited",
            "lastStatus": "STOPPED",
            "desiredStatus": "STOPPED",
            "containers": [
                {"name": "app", "exitCode": exit_code, "reason": reason},
            ],
        }
    }


class FakeSlackResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class FakeSlack:
    """
    Minimal stand-in for requests.post that routes Slack API calls and records them.

    Each call captures (url, payload). Default behavior:
    - chat.postMessage  -> assigns an incrementing ts (returns {"ok": True, "channel": C, "ts": ts})
    - chat.update       -> returns {"ok": True} and records the update
    - chat.delete       -> returns {"ok": True}
    """

    def __init__(self):
        self.calls = []
        self._ts_counter = 1_700_000_000
        # Optional override: map of URL-substring -> FakeSlackResponse

    def __call__(self, url, headers=None, json=None, data=None, files=None, timeout=None):
        self.calls.append({"url": url, "json": json, "data": data, "files": bool(files)})
        if url.endswith("/api/chat.postMessage"):
            self._ts_counter += 1
            ts = f"{self._ts_counter}.000100"
            return FakeSlackResponse({"ok": True, "channel": TEST_CHANNEL, "ts": ts})
        if url.endswith("/api/chat.update"):
            return FakeSlackResponse({"ok": True, "channel": json["channel"], "ts": json["ts"]})
        if url.endswith("/api/chat.delete"):
            return FakeSlackResponse({"ok": True})
        return FakeSlackResponse({"ok": False, "error": f"unhandled:{url}"}, status=200)


def _posts(fake: FakeSlack):
    return [c for c in fake.calls if c["url"].endswith("/api/chat.postMessage")]


def _updates(fake: FakeSlack):
    return [c for c in fake.calls if c["url"].endswith("/api/chat.update")]


def _deletes(fake: FakeSlack):
    return [c for c in fake.calls if c["url"].endswith("/api/chat.delete")]


@mock_aws
class CrashNotifierAggregationTests(unittest.TestCase):
    def setUp(self):
        _base_env()
        # Create DynamoDB table under moto.
        ddb = boto3.client("dynamodb", region_name="us-east-1")
        ddb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "service_key", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "service_key", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # Fresh module imports under moto context.
        for mod in ("crash_notifier", "alert_state", "slack_notifier", "ecs_utils", "logs_utils"):
            if mod in sys.modules:
                del sys.modules[mod]
        import alert_state  # noqa: E402
        import slack_notifier  # noqa: E402
        import crash_notifier  # noqa: E402

        self.alert_state = alert_state
        self.slack_notifier = slack_notifier
        self.crash_notifier = crash_notifier

        # Stub enrich_crash_data to skip real ECS/log calls.
        self.enrich_patcher = patch.object(
            crash_notifier,
            "enrich_crash_data",
            side_effect=lambda info: {**info, "recent_logs": []},
        )
        self.enrich_patcher.start()

        self.fake = FakeSlack()
        self.requests_patcher = patch("slack_notifier.requests.post", side_effect=self.fake)
        self.requests_patcher.start()

    def tearDown(self):
        self.enrich_patcher.stop()
        self.requests_patcher.stop()

    def _get_state(self, cluster="test-cluster", service="my-service", region="us-east-1"):
        key = self.alert_state.service_key(cluster, service, region)
        return self.alert_state.get_existing_state(key)

    # ---- 1. First crash opens a window, posts parent, writes ts ----
    def test_first_crash_opens_window(self):
        self.crash_notifier.lambda_handler(_sample_event("t1"), None)

        posts = _posts(self.fake)
        self.assertEqual(len(posts), 1, "should post exactly one parent message")
        self.assertEqual(len(_updates(self.fake)), 0)
        self.assertEqual(len(_deletes(self.fake)), 0)

        item = self._get_state()
        self.assertIsNotNone(item)
        self.assertEqual(int(item["crash_count"]), 1)
        self.assertEqual(item["slack_channel_id"], TEST_CHANNEL)
        self.assertTrue(item["slack_message_ts"])  # ts recorded

    # ---- 2. Second crash within window -> 1 edit + 1 thread reply, x2 header ----
    def test_second_crash_edits_and_threads(self):
        self.crash_notifier.lambda_handler(_sample_event("t1"), None)
        first_ts = self._get_state()["slack_message_ts"]

        self.crash_notifier.lambda_handler(_sample_event("t2"), None)

        posts = _posts(self.fake)
        updates = _updates(self.fake)
        self.assertEqual(len(posts), 2, "parent + thread reply = 2 postMessage calls")
        self.assertEqual(len(updates), 1, "exactly one chat.update for the edit")

        # The edit preserves the original ts.
        self.assertEqual(updates[0]["json"]["ts"], first_ts)
        # The header text carries "(x2)".
        header_block = updates[0]["json"]["blocks"][0]
        self.assertIn("x2", header_block["text"]["text"])

        # The second postMessage is a thread reply on the parent ts.
        thread_reply = posts[1]["json"]
        self.assertEqual(thread_reply["thread_ts"], first_ts)

        item = self._get_state()
        self.assertEqual(int(item["crash_count"]), 2)

    # ---- 3. 'edit' mode skips thread reply ----
    def test_edit_mode_skips_thread(self):
        os.environ["CRASH_ALERT_MODE"] = "edit"
        # Re-import crash_notifier so _alert_mode picks up new env at call time (already reads env fresh each call).
        self.crash_notifier.lambda_handler(_sample_event("t1"), None)
        self.crash_notifier.lambda_handler(_sample_event("t2"), None)

        # 1 parent post, 0 thread replies, 1 edit
        self.assertEqual(len(_posts(self.fake)), 1)
        self.assertEqual(len(_updates(self.fake)), 1)

    # ---- 4. 'thread' mode skips edit ----
    def test_thread_mode_skips_edit(self):
        os.environ["CRASH_ALERT_MODE"] = "thread"
        self.crash_notifier.lambda_handler(_sample_event("t1"), None)
        self.crash_notifier.lambda_handler(_sample_event("t2"), None)

        # 1 parent post + 1 thread reply = 2 posts, 0 updates
        self.assertEqual(len(_posts(self.fake)), 2)
        self.assertEqual(len(_updates(self.fake)), 0)
        self.assertEqual(_posts(self.fake)[1]["json"].get("thread_ts"),
                         _posts(self.fake)[0]["json"].get("ts") or self._find_first_parent_ts())

    def _find_first_parent_ts(self):
        # Fall back: read it from DynamoDB.
        return self._get_state()["slack_message_ts"]

    # ---- 5. Window expiry opens a fresh message ----
    def test_window_expiry_opens_fresh_parent(self):
        self.crash_notifier.lambda_handler(_sample_event("t1"), None)
        first_ts = self._get_state()["slack_message_ts"]

        # Force expiry by writing a past window_expires_at.
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        table = ddb.Table(TABLE_NAME)
        table.update_item(
            Key={"service_key": self.alert_state.service_key("test-cluster", "my-service", "us-east-1")},
            UpdateExpression="SET window_expires_at = :past",
            ExpressionAttributeValues={":past": 1},
        )

        self.crash_notifier.lambda_handler(_sample_event("t2"), None)

        posts = _posts(self.fake)
        self.assertEqual(len(posts), 2, "expired window triggers a new parent post, not a thread reply")
        self.assertEqual(len(_updates(self.fake)), 0)

        item = self._get_state()
        self.assertEqual(int(item["crash_count"]), 1, "new window resets crash_count")
        self.assertNotEqual(item["slack_message_ts"], first_ts)

    # ---- 6. finalize_new_message_ts race loser calls chat.delete ----
    def test_finalize_race_loser_deletes(self):
        # Pre-populate state as if another invocation already opened + finalized a parent.
        key = self.alert_state.service_key("test-cluster", "my-service", "us-east-1")
        now = int(datetime.now(timezone.utc).timestamp())
        ddb = boto3.resource("dynamodb", region_name="us-east-1")
        ddb.Table(TABLE_NAME).put_item(
            Item={
                "service_key": key,
                "crash_count": 1,
                "first_crash_ts": "2026-04-23T10:00:00Z",
                "last_crash_ts": "2026-04-23T10:00:00Z",
                "window_expires_at": now + 1800,
                "slack_channel_id": TEST_CHANNEL,
                "slack_message_ts": "1700000000.000999",
                "recent_crashes": ["{}"],
            }
        )

        # Force get_or_create to treat this as a NEW window (simulating the race
        # where our step-1 conditional write wins concurrently with another winner):
        # simplest way is to patch get_or_create_alert_state to return new=True despite
        # the existing item — this is exactly the race we're simulating.
        original = self.alert_state.get_or_create_alert_state

        def fake_get_or_create(key, crash, window_seconds):
            # Return as if we opened a fresh window (new=True), but leave the row alone
            # so finalize's condition "attribute_not_exists(slack_message_ts)" fails.
            return {
                "new": True,
                "item": {
                    "service_key": key,
                    "crash_count": 1,
                    "first_crash_ts": "2026-04-23T11:00:00Z",
                    "last_crash_ts": "2026-04-23T11:00:00Z",
                    "window_expires_at": now + 1800,
                    "recent_crashes": ["{}"],
                },
            }

        with patch.object(self.crash_notifier, "get_or_create_alert_state", side_effect=fake_get_or_create):
            self.crash_notifier.lambda_handler(_sample_event("t2"), None)

        self.assertEqual(len(_posts(self.fake)), 1, "we posted once")
        self.assertEqual(len(_deletes(self.fake)), 1, "race loser deletes its own message")

        # State still has the original winner's ts, not ours.
        item = self._get_state()
        self.assertEqual(item["slack_message_ts"], "1700000000.000999")


if __name__ == "__main__":
    unittest.main()
