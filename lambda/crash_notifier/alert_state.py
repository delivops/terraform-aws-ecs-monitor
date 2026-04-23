"""
DynamoDB-backed aggregation state for ECS crash alerts.

Opens a sliding window per service on the first crash and records repeat crashes
against that window using atomic conditional writes so concurrent Lambda
invocations (EventBridge scales wide) can't race each other.
"""

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError


dynamodb = boto3.resource("dynamodb")

RECENT_CRASHES_CAP = 10


def _table():
    table_name = os.environ["ALERT_STATE_TABLE"]
    return dynamodb.Table(table_name)


def _now_epoch() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def service_key(cluster: str, service: str, region: str) -> str:
    return f"{cluster}#{service}#{region}"


def _crash_entry(crash: Dict[str, Any]) -> str:
    """Serialize a crash into a compact JSON string for the recent_crashes list."""
    task_arn = crash.get("task_arn") or ""
    task_id = task_arn.split("/")[-1] if task_arn else "unknown"
    return json.dumps(
        {
            "task_id": task_id,
            "container_failures": crash.get("container_reason")
            or crash.get("stopped_reason")
            or "",
            "exit_code": crash.get("exit_code"),
            "ts": _now_iso(),
        }
    )


def get_or_create_alert_state(
    key: str, current_crash: Dict[str, Any], window_seconds: int
) -> Dict[str, Any]:
    """
    Open a new window or record a repeat crash against the live window.

    Returns:
        {"new": True,  "item": {...}}  — new window opened; caller must post parent.
        {"new": False, "item": {...}}  — live window; caller should edit/thread-reply.
    """
    table = _table()
    now = _now_epoch()
    now_iso = _now_iso()
    expires_at = now + window_seconds
    entry = _crash_entry(current_crash)

    try:
        resp = table.update_item(
            Key={"service_key": key},
            UpdateExpression=(
                "SET crash_count = :one, "
                "first_crash_ts = :now_iso, "
                "last_crash_ts = :now_iso, "
                "window_expires_at = :expires, "
                "recent_crashes = :entry_list "
                "REMOVE slack_message_ts, slack_channel_id"
            ),
            ConditionExpression=(
                "attribute_not_exists(service_key) OR window_expires_at < :now"
            ),
            ExpressionAttributeValues={
                ":one": 1,
                ":now": now,
                ":now_iso": now_iso,
                ":expires": expires_at,
                ":entry_list": [entry],
            },
            ReturnValues="ALL_NEW",
        )
        return {"new": True, "item": resp["Attributes"]}
    except ClientError as e:
        if e.response["Error"]["Code"] != "ConditionalCheckFailedException":
            raise

    # Live window exists — increment.
    resp = table.update_item(
        Key={"service_key": key},
        UpdateExpression=(
            "ADD crash_count :one "
            "SET last_crash_ts = :now_iso, "
            "window_expires_at = :expires, "
            "recent_crashes = list_append("
            "if_not_exists(recent_crashes, :empty), :entry_list)"
        ),
        ExpressionAttributeValues={
            ":one": 1,
            ":now_iso": now_iso,
            ":expires": expires_at,
            ":entry_list": [entry],
            ":empty": [],
        },
        ReturnValues="ALL_NEW",
    )
    item = resp["Attributes"]

    # Cap recent_crashes at RECENT_CRASHES_CAP (keep the most recent).
    recent = item.get("recent_crashes") or []
    if len(recent) > RECENT_CRASHES_CAP:
        trimmed = recent[-RECENT_CRASHES_CAP:]
        table.update_item(
            Key={"service_key": key},
            UpdateExpression="SET recent_crashes = :trimmed",
            ExpressionAttributeValues={":trimmed": trimmed},
        )
        item["recent_crashes"] = trimmed

    return {"new": False, "item": item}


def finalize_new_message_ts(key: str, channel: str, ts: str) -> bool:
    """
    Record the Slack ts of a freshly posted parent message.

    Returns True on success, False if another invocation beat us to it (caller
    should delete their duplicate Slack message).
    """
    table = _table()
    try:
        table.update_item(
            Key={"service_key": key},
            UpdateExpression="SET slack_message_ts = :ts, slack_channel_id = :ch",
            ConditionExpression="attribute_not_exists(slack_message_ts)",
            ExpressionAttributeValues={":ts": ts, ":ch": channel},
        )
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
            return False
        raise


def get_existing_state(key: str) -> Optional[Dict[str, Any]]:
    """Read the current state item (used when handling a repeat crash)."""
    resp = _table().get_item(Key={"service_key": key}, ConsistentRead=True)
    return resp.get("Item")
