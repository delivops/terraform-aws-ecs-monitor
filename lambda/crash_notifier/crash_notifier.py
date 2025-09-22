"""
ECS Crash Notifier Lambda Function

Main entry point for processing ECS crash events and sending notifications.
This module orchestrates the workflow using specialized utility modules.
"""

import json
from typing import Dict, Any

# Import our utility modules
from slack_notifier import SlackNotifier
from ecs_utils import extract_crash_info, enrich_crash_data


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Process ECS crash events and send enriched notifications to Slack
    """
    try:
        # Extract event details
        detail = event.get('detail', {})
        crash_info = extract_crash_info(detail)
        
        # Enrich with additional data
        enriched_info = enrich_crash_data(crash_info)
        
        # Send to Slack using bot API
        slack_notifier = SlackNotifier()
        success = slack_notifier.send_crash_notification(enriched_info)
        
        if success:
            print("Crash notification sent successfully via Slack bot")
        else:
            print("Failed to send crash notification via Slack bot")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Crash notification processed successfully',
                'taskArn': crash_info.get('task_arn'),
                'slackNotificationSent': success
            })
        }
        
    except Exception as e:
        print(f"Error processing crash event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }
