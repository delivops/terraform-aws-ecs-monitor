"""
Slack notification module for ECS crash events.
Handles all Slack-related functionality including message formatting and file uploads.
"""

import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple


class SlackNotifier:
    """Handles Slack notifications for ECS crash events using Bot API."""
    
    def __init__(self, bot_token: str = None, channel: str = None):
        self.bot_token = bot_token or os.environ.get('SLACK_BOT_TOKEN')
        self.channel = channel or os.environ.get('SLACK_CHANNEL')
    
    def _send_message(self, payload: Dict, message_type: str) -> Tuple[bool, Optional[str]]:
        """Send a message using Slack Web API."""
        if not self.bot_token:
            print("❌ SLACK_BOT_TOKEN not configured. Cannot send Slack notifications.")
            return False, None
            
        if not self.channel:
            print("❌ SLACK_CHANNEL not configured. Cannot send Slack notifications.")
            return False, None
            
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/json"
        }
        
        # Add channel to payload
        payload["channel"] = self.channel
        
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("ok"):
                ts = result.get("ts")
                print(f"✅ {message_type} Slack message sent successfully!")
                return True, ts
            else:
                print(f"❌ Slack API error for {message_type}: {result.get('error', 'Unknown error')}")
                return False, None
                
        except Exception as e:
            print(f"❌ Failed to send {message_type} Slack message: {e}")
            return False, None
    
    def send_crash_notification(self, crash_info: Dict[str, Any]) -> bool:
        """Send crash notification with logs as attachment."""
        
        if not self.bot_token or not self.channel:
            print("❌ SLACK_BOT_TOKEN and SLACK_CHANNEL must be configured for Slack notifications.")
            return False
        
        # Create blocks for the message
        blocks = self._create_crash_blocks(crash_info)
        
        # If we have logs, send with attachment
        if crash_info.get('recent_logs'):
            return self._send_message_with_file(blocks, crash_info)
        else:
            # Send just the message without attachment
            payload = {
                "blocks": blocks,
                "text": f"🚨 Task Crash: {crash_info['service_name']} in {crash_info['cluster_name']}"  # Fallback text for notifications
            }
            success, _ = self._send_message(payload, "Crash notification")
            return success
    
    def _create_crash_blocks(self, crash_info: Dict[str, Any]) -> list:
        """Create Slack blocks for crash notification."""
        # Format started time
        started_at = crash_info.get('started_at', '')
        formatted_started_time = 'N/A'
        if started_at:
            try:
                started_time = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                formatted_started_time = started_time.strftime('%Y-%m-%d %H:%M:%S UTC')
            except Exception:
                formatted_started_time = started_at
        
        # Create AWS console link for the service
        aws_region = crash_info.get('cluster_arn', '').split(':')[3] if crash_info.get('cluster_arn') else 'us-east-1'
        service_url = f"https://{aws_region}.console.aws.amazon.com/ecs/v2/clusters/{crash_info['cluster_name']}/services/{crash_info['service_name']}/health"
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Task Crash Detected: {crash_info['service_name']} ({crash_info['cluster_name']})",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Service* <{service_url}|{crash_info['service_name']}> in {crash_info['cluster_name']}"
                }
            },
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Task Definition Version:*\n{crash_info.get('task_definition_version', 'N/A')}"
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Started Time:*\n{formatted_started_time}"
                    }
                ]
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Reason:* {self._format_crash_reason(crash_info)}"
                }
            }
        ]
        
        # Add task ARN for debugging
        task_id = crash_info['task_arn'].split('/')[-1] if crash_info['task_arn'] else 'unknown'
        context_elements = [
            {
                "type": "mrkdwn",
                "text": f"Task ID: `{task_id}`"
            }
        ]
        
        # Add UI links based on log source
        if crash_info.get('log_source') == 'coralogix':
            from coralogix_utils import generate_coralogix_ui_link
            ui_link = generate_coralogix_ui_link(crash_info)
            if ui_link:
                context_elements.append({
                    "type": "mrkdwn",
                    "text": f"<{ui_link}|View logs in Coralogix>"
                })
        elif crash_info.get('log_source') == 'elasticsearch':
            from elasticsearch_utils import generate_elasticsearch_ui_link
            ui_link = generate_elasticsearch_ui_link(crash_info)
            if ui_link:
                context_elements.append({
                    "type": "mrkdwn",
                    "text": f"<{ui_link}|View logs in Kibana>"
                })
        
        blocks.append({
            "type": "context",
            "elements": context_elements
        })
        
        return blocks
    
    def _format_crash_reason(self, crash_info: Dict[str, Any]) -> str:
        """Format the crash reason with container details."""
        container_reason = crash_info.get('container_reason', '')
        task_reason = crash_info.get('stopped_reason', '')
        failed_container = crash_info.get('failed_container', {})
        container_name = failed_container.get('name', 'unknown') if failed_container else 'unknown'
        exit_code = crash_info.get('exit_code')
        
        # Handle launch failures (no exit code)
        if exit_code is None:
            if container_reason:
                return f"Launch failure: {container_reason}"
            elif task_reason:
                return f"Launch failure: {task_reason}"
            else:
                return "Launch failure: Unknown reason"
        
        # Handle runtime failures (with exit code)
        if container_reason:
            reason_text = f"[{container_name}] Exit code: {exit_code}, reason: \"{container_reason}\""
        elif task_reason:
            # Fallback to task-level reason if no container-specific reason
            reason_text = f"[{container_name}] Exit code: {exit_code}, task reason: \"{task_reason}\""
        else:
            # Last resort
            reason_text = f"[{container_name}] Exit code: {exit_code}, reason: Unknown"
            
        return reason_text
    
    def _send_message_with_file(self, blocks: list, crash_info: Dict[str, Any]) -> bool:
        """Send a single message with both blocks and file attachment using modern Slack API."""
        if not self.bot_token or not self.channel:
            print("❌ Cannot send message with file without SLACK_BOT_TOKEN and SLACK_CHANNEL")
            return False
        
        service_name = crash_info.get('service_name', 'unknown')
        task_id = crash_info['task_arn'].split('/')[-1] if crash_info['task_arn'] else 'unknown'
        safe_service_name = "".join(c for c in service_name if c.isalnum() or c in (' ', '-', '_')).strip()
        filename = f"{safe_service_name}_{task_id}_logs.txt"
        
        # Create file content
        file_content = self._create_log_file_content(crash_info)
        
        # Step 1: Get upload URL using files.getUploadURLExternal
        upload_url_endpoint = "https://slack.com/api/files.getUploadURLExternal"
        headers = {
            "Authorization": f"Bearer {self.bot_token}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        
        upload_url_payload = {
            "filename": filename,
            "length": str(len(file_content.encode('utf-8')))
        }
        
        try:
            # Get upload URL using form data
            upload_url_response = requests.post(upload_url_endpoint, headers=headers, data=upload_url_payload, timeout=30)
            upload_url_response.raise_for_status()
            
            upload_url_result = upload_url_response.json()
            
            if not upload_url_result.get("ok"):
                print(f"❌ Failed to get upload URL: {upload_url_result.get('error', 'Unknown error')}")
                return False
            
            upload_url = upload_url_result.get("upload_url")
            file_id = upload_url_result.get("file_id")
            
            if not upload_url or not file_id:
                print("❌ Missing upload_url or file_id in response")
                return False
            
            # Step 2: Upload file to the URL
            upload_response = requests.post(upload_url, files={'file': (filename, file_content, 'text/plain')}, timeout=30)
            upload_response.raise_for_status()
            
            # Step 3: Complete the upload using files.completeUploadExternal with blocks
            complete_upload_endpoint = "https://slack.com/api/files.completeUploadExternal"
            complete_headers = {
                "Authorization": f"Bearer {self.bot_token}",
                "Content-Type": "application/json"
            }
            
            complete_upload_payload = {
                "files": [
                    {
                        "id": file_id,
                        "title": f"Crash logs for {service_name} (Task: {task_id})"
                    }
                ],
                "channel_id": self.channel,
                "blocks": blocks
            }
            
            complete_response = requests.post(complete_upload_endpoint, headers=complete_headers, json=complete_upload_payload, timeout=30)
            complete_response.raise_for_status()
            
            complete_result = complete_response.json()
            
            if complete_result.get("ok"):
                print(f"✅ Sent crash notification with blocks and attached log file: {filename}")
                return True
            else:
                print(f"❌ Failed to complete file upload {filename}: {complete_result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to send message with file {filename}: {e}")
            return False
    
    def _create_log_file_content(self, crash_info: Dict[str, Any]) -> str:
        """Create the log file content for the crash."""
        lines = []
        
        # Add header with log source information
        log_source = crash_info.get('log_source', 'unknown')
        print(f"🐛 DEBUG Slack file: log_source from crash_info = '{log_source}'")
        print(f"🐛 DEBUG Slack file: crash_info keys = {list(crash_info.keys())}")
        lines.append(f"LOG SOURCE: {log_source.upper()}")
        lines.append("-" * 80)
        lines.append("")
        
        # Add logs if available
        recent_logs = crash_info.get('recent_logs', [])
        if recent_logs:
            lines.append("CONTAINER LOGS:")
            lines.append("-" * 80)
            lines.append("")
            
            for log_entry in recent_logs:
                # Just show the raw message without timestamp prefix
                lines.append(log_entry.get('message', ''))
            
            lines.append("")
        else:
            lines.append("No logs available for this crash.")
        
        return "\n".join(lines)