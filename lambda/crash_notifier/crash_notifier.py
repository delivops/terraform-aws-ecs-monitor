"""
ECS Crash Notifier Lambda Function

Main entry point for processing ECS crash events and sending notifications.
This module orchestrates the workflow using specialized utility modules.
"""

import json
import os
from typing import Dict, Any

from slack_notifier import SlackNotifier
from ecs_utils import extract_crash_info, enrich_crash_data
from alert_state import (
    service_key,
    get_or_create_alert_state,
    finalize_new_message_ts,
)


DEFAULT_WINDOW_MINUTES = 30
VALID_MODES = ("edit", "thread", "edit_and_thread")


def _window_seconds() -> int:
    try:
        minutes = int(os.environ.get("AGGREGATION_WINDOW_MINUTES", DEFAULT_WINDOW_MINUTES))
    except ValueError:
        minutes = DEFAULT_WINDOW_MINUTES
    return max(1, minutes) * 60


def _alert_mode() -> str:
    mode = os.environ.get("CRASH_ALERT_MODE", "edit_and_thread")
    return mode if mode in VALID_MODES else "edit_and_thread"


def _build_thread_reply_text(crash_info: Dict[str, Any], crash_count: int) -> str:
    task_arn = crash_info.get("task_arn") or ""
    task_id = task_arn.split("/")[-1] if task_arn else "unknown"
    reason = crash_info.get("container_reason") or crash_info.get("stopped_reason") or "unknown"
    exit_code = crash_info.get("exit_code")
    exit_str = f"exit {exit_code}" if exit_code is not None else "launch failure"
    return f"Repeat crash #{crash_count}: Task `{task_id}` — {exit_str} — {reason}"


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Process ECS crash events and send enriched, deduplicated notifications to Slack."""
    try:
        detail = event.get("detail", {})
        crash_info = extract_crash_info(detail)
        enriched = enrich_crash_data(crash_info)

        cluster_arn = enriched.get("cluster_arn", "") or ""
        region = cluster_arn.split(":")[3] if cluster_arn.count(":") >= 3 else os.environ.get("AWS_REGION", "us-east-1")
        key = service_key(enriched["cluster_name"], enriched["service_name"], region)

        state = get_or_create_alert_state(key, enriched, _window_seconds())
        notifier = SlackNotifier()

        if state["new"]:
            ok, channel, ts = notifier.post_new_alert(enriched, aggregation=state["item"])
            if not ok or not ts or not channel:
                print("❌ Failed to post new parent alert or capture ts")
                return _response(200, enriched, slack_ok=ok, action="new_post_failed")

            won = finalize_new_message_ts(key, channel, ts)
            if not won:
                print("⚠️  Lost ts-write race — deleting duplicate Slack message")
                notifier.delete_message(channel, ts)
                return _response(200, enriched, slack_ok=True, action="race_lost_deleted")

            return _response(200, enriched, slack_ok=True, action="new_parent_posted")

        item = state["item"]
        channel = item.get("slack_channel_id")
        ts = item.get("slack_message_ts")
        crash_count = int(item.get("crash_count", 1))

        if not channel or not ts:
            # Previous invocation opened the window but hasn't finalized the ts yet.
            # Post a thread-less reply is not possible; skip silently to avoid dup parents.
            print("⚠️  Live window has no slack_message_ts yet — skipping this repeat")
            return _response(200, enriched, slack_ok=False, action="skipped_pending_parent")

        mode = _alert_mode()
        did_anything = False

        if mode in ("edit", "edit_and_thread"):
            blocks = notifier._create_crash_blocks(enriched, aggregation=item)
            text = f"🚨 ECS Crash Loop: {enriched['service_name']} (x{crash_count})"
            did_anything = notifier.update_alert(channel, ts, blocks, text) or did_anything

        if mode in ("thread", "edit_and_thread"):
            reply_text = _build_thread_reply_text(enriched, crash_count)
            did_anything = notifier.reply_in_thread(channel, ts, reply_text) or did_anything

        return _response(200, enriched, slack_ok=did_anything, action=f"aggregated_{mode}")

    except Exception as e:
        print(f"Error processing crash event: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def _response(status: int, crash_info: Dict[str, Any], slack_ok: bool, action: str) -> Dict[str, Any]:
    return {
        "statusCode": status,
        "body": json.dumps(
            {
                "message": "Crash notification processed",
                "taskArn": crash_info.get("task_arn"),
                "slackNotificationSent": slack_ok,
                "action": action,
            }
        ),
    }
