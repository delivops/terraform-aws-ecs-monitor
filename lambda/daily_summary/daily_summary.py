"""
Daily Summary Lambda Function

This function analyzes crash events from CloudWatch logs and sends a comprehensive
daily summary to Slack with insights, trends, and statistics.
"""

import json
import boto3
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter
import requests


class DailySummaryProcessor:
    """Processes crash events and generates daily summaries."""
    
    def __init__(self):
        self.logs_client = boto3.client('logs')
        self.cluster_name = os.environ.get('CLUSTER_NAME', 'unknown')
        self.log_group_name = f"/aws/ecs/monitoring/{self.cluster_name}/crash-events"
        self.slack_bot_token = os.environ.get('SLACK_BOT_TOKEN')
        self.slack_channel = os.environ.get('SLACK_CHANNEL')
        
    def get_crash_events_from_last_24_hours(self) -> List[Dict[str, Any]]:
        """Retrieve all crash events from the last 24 hours."""
        try:
            # Calculate last 24 hours
            now = datetime.now(timezone.utc)
            twenty_four_hours_ago = now - timedelta(hours=24)
            
            # Convert to timestamps
            start_time = int(twenty_four_hours_ago.timestamp() * 1000)
            end_time = int(now.timestamp() * 1000)
            
            print(f"Querying crash events from {twenty_four_hours_ago} to {now} (last 24 hours)")
            
            # Query CloudWatch logs
            events = []
            next_token = None
            
            while True:
                params = {
                    'logGroupName': self.log_group_name,
                    'startTime': start_time,
                    'endTime': end_time,
                    'filterPattern': '',  # Get all events
                }
                
                if next_token:
                    params['nextToken'] = next_token
                
                try:
                    response = self.logs_client.filter_log_events(**params)
                    
                    for event in response.get('events', []):
                        try:
                            # Parse the JSON message
                            message_data = json.loads(event['message'])
                            events.append({
                                'timestamp': event['timestamp'],
                                'message': message_data,
                                'ingestion_time': event['ingestionTime']
                            })
                        except json.JSONDecodeError:
                            print(f"Failed to parse log event: {event['message']}")
                            continue
                    
                    next_token = response.get('nextToken')
                    if not next_token:
                        break
                        
                except Exception as e:
                    print(f"Error querying CloudWatch logs: {str(e)}")
                    break
            
            print(f"Retrieved {len(events)} crash events from the last 24 hours")
            return events
            
        except Exception as e:
            print(f"Error retrieving crash events: {str(e)}")
            return []
    
    def analyze_crash_events(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze crash events and generate insights."""
        if not events:
            return {
                'total_crashes': 0,
                'services_affected': [],
                'crash_reasons': {},
                'hourly_distribution': {},
                'container_failures': {},
                'exit_codes': {},
                'task_definitions': {},
                'trends': {},
                'top_issues': []
            }
        
        # Initialize analysis containers
        services = set()
        crash_reasons = Counter()
        hourly_crashes = defaultdict(int)
        container_failures = Counter()
        exit_codes = Counter()
        task_definitions = Counter()
        service_crashes = Counter()
        
        for event in events:
            try:
                detail = event['message'].get('detail', {})
                
                # Extract service information
                cluster_arn = detail.get('clusterArn', '')
                service_name = self._extract_service_name(detail)
                if service_name:
                    services.add(service_name)
                    service_crashes[service_name] += 1
                
                # Extract crash reason
                stopped_reason = detail.get('stoppedReason', 'Unknown')
                crash_reasons[stopped_reason] += 1
                
                # Hourly distribution
                timestamp = event['timestamp']
                dt = datetime.fromtimestamp(timestamp / 1000, timezone.utc)
                hour = dt.hour
                hourly_crashes[hour] += 1
                
                # Container failures and exit codes
                containers = detail.get('containers', [])
                for container in containers:
                    if container.get('exitCode') is not None and container.get('exitCode') != 0:
                        container_name = container.get('name', 'unknown')
                        container_failures[container_name] += 1
                        exit_code = container.get('exitCode')
                        exit_codes[exit_code] += 1
                
                # Task definition versions
                task_def_arn = detail.get('taskDefinitionArn', '')
                if task_def_arn:
                    task_def_name = task_def_arn.split('/')[-1] if '/' in task_def_arn else task_def_arn
                    task_definitions[task_def_name] += 1
                    
            except Exception as e:
                print(f"Error analyzing event: {str(e)}")
                continue
        
        # Generate top issues
        top_issues = []
        
        # Top crash reasons
        top_reasons = crash_reasons.most_common(3)
        if top_reasons:
            top_issues.append({
                'type': 'crash_reasons',
                'title': 'Top Crash Reasons',
                'items': [f"{reason}: {count} crashes" for reason, count in top_reasons]
            })
        
        # Most affected services
        top_services = service_crashes.most_common(3)
        if top_services:
            top_issues.append({
                'type': 'affected_services',
                'title': 'Most Affected Services',
                'items': [f"{service}: {count} crashes" for service, count in top_services]
            })
        
        # Top exit codes
        top_exit_codes = exit_codes.most_common(3)
        if top_exit_codes:
            top_issues.append({
                'type': 'exit_codes',
                'title': 'Common Exit Codes',
                'items': [f"Exit {code}: {count} occurrences" for code, count in top_exit_codes]
            })
        
        return {
            'total_crashes': len(events),
            'services_affected': list(services),
            'crash_reasons': dict(crash_reasons),
            'hourly_distribution': dict(hourly_crashes),
            'container_failures': dict(container_failures),
            'exit_codes': dict(exit_codes),
            'task_definitions': dict(task_definitions),
            'service_crashes': dict(service_crashes),
            'top_issues': top_issues
        }
    
    def _extract_service_name(self, detail: Dict[str, Any]) -> Optional[str]:
        """Extract service name from task detail."""
        try:
            group = detail.get('group', '')
            if group.startswith('service:'):
                return group.replace('service:', '')
            return None
        except Exception:
            return None
    
    def create_slack_summary_blocks(self, analysis: Dict[str, Any], date: str) -> List[Dict[str, Any]]:
        """Create Slack blocks for the daily summary."""
        blocks = []
        
        # Header
        total_crashes = analysis['total_crashes']
        if total_crashes == 0:
            emoji = "✅"
            status = "No crashes detected"
        elif total_crashes <= 5:
            emoji = "⚠️"
            status = f"{total_crashes} crashes detected"
        else:
            emoji = "🚨"
            status = f"{total_crashes} crashes detected"
        
        blocks.append({
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"{emoji} Daily Crash Summary - {date}",
                "emoji": True
            }
        })
        
        if total_crashes == 0:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🎉 *Great news!* No crashes were detected in the last 24 hours in the `{self.cluster_name}` cluster."
                }
            })
            return blocks
        
        # Summary section
        services_count = len(analysis['services_affected'])
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{status}* across *{services_count} service(s)* in the `{self.cluster_name}` cluster."
            }
        })
        
        # Top issues
        if analysis['top_issues']:
            blocks.append({
                "type": "divider"
            })
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🔍 Key Insights*"
                }
            })
            
            for issue in analysis['top_issues']:
                issue_text = f"*{issue['title']}:*\n"
                for item in issue['items']:
                    issue_text += f"• {item}\n"
                
                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": issue_text.strip()
                    }
                })
        
        # Hourly distribution if we have crashes
        if analysis['hourly_distribution']:
            blocks.append({
                "type": "divider"
            })
            hourly_text = "*🕐 Hourly Distribution (UTC):*\n"
            sorted_hours = sorted(analysis['hourly_distribution'].items())
            for hour, count in sorted_hours:
                hourly_text += f"• {hour:02d}:00 - {count} crash{'es' if count != 1 else ''}\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": hourly_text.strip()
                }
            })
        
        # Affected services
        if analysis['services_affected']:
            blocks.append({
                "type": "divider"
            })
            services_text = "*🔧 Affected Services:*\n"
            for service in sorted(analysis['services_affected']):
                crash_count = analysis['service_crashes'].get(service, 0)
                services_text += f"• `{service}` - {crash_count} crash{'es' if crash_count != 1 else ''}\n"
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": services_text.strip()
                }
            })
        
        # Add context
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Cluster: `{self.cluster_name}` | Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}"
                }
            ]
        })
        
        return blocks
    
    def send_slack_summary(self, blocks: List[Dict[str, Any]]) -> bool:
        """Send the daily summary to Slack."""
        if not self.slack_bot_token or not self.slack_channel:
            print("❌ SLACK_BOT_TOKEN and SLACK_CHANNEL must be configured for Slack notifications.")
            return False
        
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.slack_bot_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "channel": self.slack_channel,
            "blocks": blocks,
            "text": f"Daily Crash Summary - {self.cluster_name}"  # Fallback text
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                print("✅ Daily summary sent to Slack successfully!")
                return True
            else:
                print(f"❌ Slack API error: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send daily summary to Slack: {e}")
            return False


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda handler for generating daily crash summaries.
    """
    try:
        print("🚀 Starting daily crash summary generation...")
        
        # Initialize processor
        processor = DailySummaryProcessor()
        
        # Get current time for the summary
        now = datetime.now(timezone.utc)
        date_str = now.strftime('%Y-%m-%d')
        
        # Retrieve crash events
        print("📊 Retrieving crash events from CloudWatch...")
        events = processor.get_crash_events_from_last_24_hours()
        
        # Analyze events
        print("🔍 Analyzing crash patterns...")
        analysis = processor.analyze_crash_events(events)
        
        # Create Slack summary
        print("📝 Creating Slack summary...")
        blocks = processor.create_slack_summary_blocks(analysis, date_str)
        
        # Send to Slack
        print("📤 Sending summary to Slack...")
        success = processor.send_slack_summary(blocks)
        
        # Prepare response
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Daily summary processed successfully',
                'date': date_str,
                'total_crashes': analysis['total_crashes'],
                'services_affected': len(analysis['services_affected']),
                'slack_sent': success
            })
        }
        
        print(f"✅ Daily summary completed for {date_str}")
        print(f"📈 Summary: {analysis['total_crashes']} crashes across {len(analysis['services_affected'])} services")
        
        return response
        
    except Exception as e:
        print(f"❌ Error processing daily summary: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': 'Failed to process daily summary',
                'message': str(e)
            })
        }
