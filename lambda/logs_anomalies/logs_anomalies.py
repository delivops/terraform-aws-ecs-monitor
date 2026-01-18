"""
CloudWatch Logs Anomaly Notifier Lambda

Scheduled via EventBridge to run every 5 minutes.
Lists anomalies from log groups matching multiple patterns, compares with DynamoDB state,
and sends new anomalies to Slack.

Environment Variables:
    LOG_GROUP_PREFIXES: JSON array of log group prefixes to monitor (e.g., '["/ecs/production", "/aws/lambda/"]')
    DYNAMODB_TABLE: DynamoDB table name for state tracking
    SLACK_BOT_TOKEN: Slack Bot OAuth token
    SLACK_CHANNEL: Slack channel for notifications
    PRIORITY_FILTER: Comma-separated priorities to notify (e.g., "HIGH,MEDIUM")
    TTL_DAYS: Number of days to keep notification records in DynamoDB (default: 7)
"""

import os
import json
import logging
import hashlib
from datetime import datetime, timedelta

import boto3
import requests
from botocore.exceptions import ClientError

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Clients
logs_client = boto3.client("logs")
dynamodb = boto3.resource("dynamodb")

# Environment variables
LOG_GROUP_PREFIXES = json.loads(os.environ.get("LOG_GROUP_PREFIXES", '["/ecs/"]'))
DYNAMODB_TABLE = os.environ.get("DYNAMODB_TABLE", "anomaly-notifier-state")
SLACK_BOT_TOKEN = os.environ.get("SLACK_BOT_TOKEN")
SLACK_CHANNEL = os.environ.get("SLACK_CHANNEL", "#alerts")
PRIORITY_FILTER = os.environ.get("PRIORITY_FILTER", "HIGH,MEDIUM").split(",")
TTL_DAYS = int(os.environ.get("TTL_DAYS", "7"))


def handler(event, context):
    """Main Lambda handler."""
    logger.info(f"Starting anomaly check for log group prefixes: {LOG_GROUP_PREFIXES}")
    
    # 1. List all anomaly detectors for matching log groups across all prefixes
    seen_detector_arns = set()
    detectors = []
    for prefix in LOG_GROUP_PREFIXES:
        prefix_detectors = list_anomaly_detectors(prefix)
        for detector in prefix_detectors:
            detector_arn = detector["anomalyDetectorArn"]
            if detector_arn not in seen_detector_arns:
                seen_detector_arns.add(detector_arn)
                detectors.append(detector)
    
    logger.info(f"Found {len(detectors)} unique anomaly detectors across {len(LOG_GROUP_PREFIXES)} prefixes")
    
    if not detectors:
        logger.info("No anomaly detectors found")
        return {"statusCode": 200, "body": "No detectors found"}
    
    # 2. List all active anomalies
    all_anomalies = []
    for detector in detectors:
        detector_arn = detector["anomalyDetectorArn"]
        anomalies = list_anomalies_for_detector(detector_arn)
        if anomalies:
            logger.info(f"Detector {detector_arn}: found {len(anomalies)} anomalies")
        all_anomalies.extend(anomalies)
    
    logger.info(f"Found {len(all_anomalies)} total anomalies across all detectors")
    
    # 3. Filter by priority
    filtered_anomalies = [
        a for a in all_anomalies 
        if a.get("priority") in PRIORITY_FILTER
    ]
    logger.info(f"After priority filter: {len(filtered_anomalies)} anomalies")
    
    # 4. Compare with DynamoDB state and find new ones
    table = dynamodb.Table(DYNAMODB_TABLE)
    new_anomalies = []
    
    for anomaly in filtered_anomalies:
        anomaly_hash = compute_anomaly_hash(anomaly)
        if not is_already_notified(table, anomaly_hash):
            new_anomalies.append(anomaly)
            record_notification(table, anomaly, anomaly_hash)
    
    logger.info(f"New anomalies to notify: {len(new_anomalies)}")
    
    # 5. Send Slack notifications
    for anomaly in new_anomalies:
        send_slack_notification(anomaly)
    
    return {
        "statusCode": 200,
        "body": json.dumps({
            "detectors_checked": len(detectors),
            "total_anomalies": len(all_anomalies),
            "new_notifications_sent": len(new_anomalies)
        })
    }


def list_anomaly_detectors(log_group_prefix: str) -> list:
    """List all anomaly detectors for log groups matching the prefix."""
    detectors = []
    paginator = logs_client.get_paginator("describe_log_groups")
    
    # First, get all log groups matching the prefix
    log_group_arns = {}
    for page in paginator.paginate(logGroupNamePrefix=log_group_prefix):
        for lg in page.get("logGroups", []):
            # Normalize ARN by removing trailing :*
            normalized_arn = lg["arn"].rstrip(":*")
            log_group_arns[normalized_arn] = lg["logGroupName"]
    
    logger.info(f"Found {len(log_group_arns)} log groups matching prefix '{log_group_prefix}'")
    
    # Now list all anomaly detectors and filter by our log groups
    detector_paginator = logs_client.get_paginator("list_log_anomaly_detectors")
    
    for page in detector_paginator.paginate():
        for detector in page.get("anomalyDetectors", []):
            # Check if this detector monitors any of our log groups
            detector_log_groups = detector.get("logGroupArnList", [])
            for arn in detector_log_groups:
                # Normalize ARN by removing trailing :*
                normalized_detector_arn = arn.rstrip(":*")
                # Check if this detector's log group is in our list
                if normalized_detector_arn in log_group_arns:
                    logger.debug(f"Matched detector {detector.get('anomalyDetectorArn')} "
                               f"for log group {log_group_arns.get(normalized_detector_arn)}")
                    detectors.append(detector)
                    break
    
    return detectors


def list_anomalies_for_detector(detector_arn: str) -> list:
    """List all active, unsuppressed anomalies for a detector."""
    anomalies = []
    active_count = 0
    inactive_count = 0
    
    try:
        paginator = logs_client.get_paginator("list_anomalies")
        for page in paginator.paginate(
            anomalyDetectorArn=detector_arn,
            suppressionState="UNSUPPRESSED"
        ):
            for anomaly in page.get("anomalies", []):
                # Only include active (ongoing) anomalies
                # 'active=True' means "Anomalies ongoing" in the CloudWatch console
                # 'active=False' means "Anomalies identified but no longer happening"
                if anomaly.get("active", False):
                    anomalies.append(anomaly)
                    active_count += 1
                else:
                    inactive_count += 1
        
        if inactive_count > 0:
            logger.debug(f"Skipped {inactive_count} inactive anomalies for detector {detector_arn}")
    except ClientError as e:
        logger.error(f"Error listing anomalies for {detector_arn}: {e}")
    
    return anomalies


def compute_anomaly_hash(anomaly: dict) -> str:
    """Compute a unique hash for an anomaly based on its characteristics."""
    # Use anomalyId directly - it's unique per anomaly
    # But we also include pattern to handle cases where same pattern reappears
    hash_input = f"{anomaly.get('anomalyId', '')}:{anomaly.get('patternId', '')}"
    return hashlib.sha256(hash_input.encode()).hexdigest()[:16]


def is_already_notified(table, anomaly_hash: str) -> bool:
    """Check if we've already sent a notification for this anomaly."""
    try:
        response = table.get_item(Key={"anomaly_hash": anomaly_hash})
        return "Item" in response
    except ClientError as e:
        logger.error(f"Error checking DynamoDB: {e}")
        return False


def record_notification(table, anomaly: dict, anomaly_hash: str):
    """Record that we've sent a notification for this anomaly."""
    ttl = int((datetime.utcnow() + timedelta(days=TTL_DAYS)).timestamp())
    
    # Extract service name from log group
    log_groups = anomaly.get("logGroupArnList", [])
    service_name = extract_service_name(log_groups[0] if log_groups else "")
    
    try:
        table.put_item(Item={
            "anomaly_hash": anomaly_hash,
            "anomaly_id": anomaly.get("anomalyId", ""),
            "pattern_id": anomaly.get("patternId", ""),
            "service_name": service_name,
            "priority": anomaly.get("priority", ""),
            "first_seen": anomaly.get("firstSeen", 0),
            "notified_at": int(datetime.utcnow().timestamp()),
            "ttl": ttl
        })
    except ClientError as e:
        logger.error(f"Error writing to DynamoDB: {e}")


def extract_service_name(log_group_arn: str) -> str:
    """Extract service name from log group ARN or name."""
    # ARN format: arn:aws:logs:region:account:log-group:/ecs/cluster/service:*
    # We want to extract the service name
    try:
        # Remove ARN prefix and trailing :*
        log_group_name = log_group_arn.split("log-group:")[-1].rstrip(":*")
        # Split by / and get last part
        parts = log_group_name.strip("/").split("/")
        return parts[-1] if parts else "unknown"
    except Exception:
        return "unknown"


def send_slack_notification(anomaly: dict):
    """Send a Slack notification for an anomaly."""
    if not SLACK_BOT_TOKEN:
        logger.warning("SLACK_BOT_TOKEN not set, skipping notification")
        return
    
    # Extract info
    log_groups = anomaly.get("logGroupArnList", [])
    service_name = extract_service_name(log_groups[0] if log_groups else "")
    priority = anomaly.get("priority", "UNKNOWN")
    description = anomaly.get("description", "No description available")
    pattern = anomaly.get("patternString", "")
    first_seen = anomaly.get("firstSeen", 0)
    last_seen = anomaly.get("lastSeen", 0)
    log_samples = anomaly.get("logSamples", [])
    
    # Priority emoji
    priority_emoji = {
        "HIGH": "🔴",
        "MEDIUM": "🟡",
        "LOW": "🟢"
    }.get(priority, "⚪")
    
    # Format timestamps
    first_seen_str = datetime.fromtimestamp(first_seen / 1000).strftime("%Y-%m-%d %H:%M:%S UTC") if first_seen else "N/A"
    last_seen_str = datetime.fromtimestamp(last_seen / 1000).strftime("%Y-%m-%d %H:%M:%S UTC") if last_seen else "N/A"
    
    # Build log group name for CloudWatch link
    log_group_name = log_groups[0].split("log-group:")[-1].rstrip(":*") if log_groups else ""
    region = os.environ.get("AWS_REGION", "us-east-1")
    cloudwatch_url = f"https://{region}.console.aws.amazon.com/cloudwatch/home?region={region}#logsV2:log-groups/log-group/{log_group_name.replace('/', '$252F')}"
    
    # Build Slack blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔍 Log Anomaly Detected",
                "emoji": True
            }
        },
        {
            "type": "section",
            "fields": [
                {"type": "mrkdwn", "text": f"*Service:*\n{service_name}"},
                {"type": "mrkdwn", "text": f"*Priority:*\n{priority_emoji} {priority}"},
                {"type": "mrkdwn", "text": f"*First Seen:*\n{first_seen_str}"},
                {"type": "mrkdwn", "text": f"*Last Seen:*\n{last_seen_str}"}
            ]
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Description:*\n{description[:500]}"
            }
        }
    ]
    
    # Add pattern if available
    if pattern:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Pattern:*\n```{pattern[:500]}```"
            }
        })
    
    # Add log samples if available
    if log_samples:
        samples_text = "\n".join([
            f"• {sample.get('message', '')[:200]}" 
            for sample in log_samples[:3]
        ])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Sample Logs:*\n{samples_text}"
            }
        })
    
    # Add CloudWatch link
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"<{cloudwatch_url}|View in CloudWatch Console>"
        }
    })
    
    blocks.append({"type": "divider"})
    
    # Send to Slack
    try:
        response = requests.post(
            "https://slack.com/api/chat.postMessage",
            headers={
                "Authorization": f"Bearer {SLACK_BOT_TOKEN}",
                "Content-Type": "application/json"
            },
            json={
                "channel": SLACK_CHANNEL,
                "blocks": blocks,
                "text": f"Log Anomaly: {priority} priority anomaly detected in {service_name}"
            },
            timeout=10
        )
        
        result = response.json()
        if not result.get("ok"):
            logger.error(f"Slack API error: {result.get('error')}")
        else:
            logger.info(f"Sent notification to {SLACK_CHANNEL} for {service_name}")
            
    except requests.RequestException as e:
        logger.error(f"Failed to send Slack notification: {e}")


# For local testing
if __name__ == "__main__":
    # Mock event and context
    test_event = {}
    test_context = None
    
    result = handler(test_event, test_context)
    print(json.dumps(result, indent=2))