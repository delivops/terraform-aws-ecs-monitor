"""
Coralogix utilities module for retrieving logs and generating UI links.
Handles all Coralogix API calls based on the proof of concept.
"""

import os
import json
import requests
import urllib.parse
from typing import Dict, Any, List, Optional


def get_coralogix_logs(crash_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get recent logs from Coralogix using the DataPrime query API.
    Returns logs in the same format as CloudWatch logs for compatibility.
    """
    try:
        # Get Coralogix configuration from environment
        api_key = os.environ.get('CORALOGIX_API_KEY')
        region = os.environ.get('CORALOGIX_REGION')
        
        if not api_key or not region:
            print("❌ Coralogix API key or region not configured")
            return []
        
        task_arn = crash_info.get('task_arn', '')
        if not task_arn:
            print("❌ No task ARN available for Coralogix query")
            return []
        
        print(f"🔍 Retrieving logs from Coralogix for task: {task_arn}")

        crash_info['log_source'] = 'coralogix'

        logs_limit = 50
        query = f"source logs last 1h | filter $l.subsystemname ~ '{crash_info['service_name']}' | filter $d.ecs_task_arn ~ '{task_arn}' | limit {logs_limit}"
        print(f"🔍 Coralogix query: {query}")
        print(f"🔍 Task ARN being searched: {task_arn}")
        
        # Also try a broader query to see what fields are available
        debug_query = f"source logs last 1h | limit 5"
        print(f"🐛 DEBUG: Will also test broader query to see field structure: {debug_query}")
        
        # Make the API request
        url = f"https://api.{region}.coralogix.com/api/v1/dataprime/query"
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }
        payload = {
            "query": query,
            "metadata": {"tier": "TIER_ARCHIVE"}
        }
        
        print(f"📡 Making Coralogix API request to: {url}")
        print(f"🔎 Query: {query}")
        
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        
        # Parse the streaming response - Coralogix returns multiple JSON objects separated by newlines
        response_text = response.text.strip()
        
        # Split by newlines and parse each JSON object
        response_lines = [line.strip() for line in response_text.split('\n') if line.strip()]
        
        # Look for the result object (usually the second line)
        logs = []
        for i, line in enumerate(response_lines):
            try:
                line_data = json.loads(line)
                print(f"📄 Line {i+1} keys: {line_data.keys()}")
                
                # Check if this line contains the results
                if 'result' in line_data and 'results' in line_data['result']:
                    current_logs = line_data['result']['results']
                    print(f"✅ Found results in line {i+1}: {len(current_logs)} log entries")                    
                    # Extend logs instead of replacing - there might be multiple result lines
                    logs.extend(current_logs)
                    print(f"📊 Total logs collected so far: {len(logs)}")
                    print(f"📊 First few log entry keys: {[list(log.keys()) for log in logs[:3]]}")
                    # DON'T break - continue processing all result lines
            except json.JSONDecodeError as e:
                print(f"⚠️ Failed to parse line {i+1}: {e}")
                continue
        
        if not logs:
            print("⚠️ No results found in any response line")
            return []
        
        print(f"🎯 Final total logs collected: {len(logs)}")
        if logs:
            print(f"🔍 First few log entry keys: {list(logs[0].keys())[:10] if logs[0] else 'empty'}")
        
        # Convert to the format expected by the rest of the system
        log_entries = []
        for i, log in enumerate(logs):
            print(f"🔍 Processing log entry {i+1}: keys = {list(log.keys())}")
            
            # Now we have the full log entry, not just selected fields
            # Let's see what structure we actually have
            user_data = log.get('userData', '{}')
            message = 'No message'
            
            # Print the full log structure for debugging
            print(f"📋 Full log entry {i+1}: {json.dumps(log, indent=2)[:500]}...")
            
            # Try to get the full log data structure
            log_data = log.get('data', {})
            if log_data:
                # If we have structured data, try message, then log, then whole entry
                extracted_message = log_data.get('message')
                extracted_log = log_data.get('log')
                
                if extracted_message is not None and extracted_message != '':
                    message = str(extracted_message)
                    print(f"📝 Using 'data.message' field: '{message}'")
                elif extracted_log is not None and extracted_log != '':
                    message = str(extracted_log)
                    print(f"📝 Message null/empty, using 'data.log' field: '{message}'")
                else:
                    message = str(log_data)
                    print(f"📝 Using whole data entry: '{message}'")
            else:
                # Fallback to userData parsing
                try:
                    parsed_data = json.loads(user_data)
                    extracted_message = parsed_data.get('message')
                    extracted_log = parsed_data.get('log')
                    
                    if extracted_message is not None and extracted_message != '':
                        message = str(extracted_message)
                        print(f"📝 Using userData 'message' field: '{message}'")
                    elif extracted_log is not None and extracted_log != '':
                        message = str(extracted_log)
                        print(f"📝 Message null/empty, using userData 'log' field: '{message}'")
                    else:
                        message = str(parsed_data)
                        print(f"📝 Using whole userData entry: '{message}'")
                        
                except (json.JSONDecodeError, TypeError) as e:
                    print(f"⚠️ Failed to parse userData as JSON: {e}")
                    print(f"⚠️ Raw userData: {user_data}")
                    print(f"⚠️ Full log entry keys: {log.keys()}")
                    # Use the raw userData or the whole log entry
                    message = str(user_data) if user_data else str(log)
            
            # Extract timestamp from metadata (as shown in proof of concept)
            timestamp_str = None
            for meta in log.get('metadata', []):
                if meta.get('key') == 'timestamp':
                    timestamp_str = meta.get('value')
                    break
            
            # Convert timestamp to milliseconds (CloudWatch format)
            timestamp_ms = 0
            if timestamp_str:
                try:
                    from datetime import datetime
                    # Handle timestamp format like: "2025-09-21T09:59:32.100026178"
                    dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    timestamp_ms = int(dt.timestamp() * 1000)
                    print(f"📅 Parsed timestamp: {timestamp_str} -> {timestamp_ms}")
                except Exception as ts_error:
                    print(f"⚠️ Error parsing timestamp {timestamp_str}: {ts_error}")
                    # Use current time as fallback
                    timestamp_ms = int(datetime.now().timestamp() * 1000)
            else:
                print(f"⚠️ No timestamp found in metadata")
                # Use current time as fallback
                from datetime import datetime
                timestamp_ms = int(datetime.now().timestamp() * 1000)
            
            log_entries.append({
                'timestamp': timestamp_ms,
                'message': message
            })
            
        print(f"🔄 Processed {len(log_entries)} log entries from Coralogix")
        
        # Sort by timestamp (newest first)
        log_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        return log_entries
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Coralogix API request failed: {e}")
        return []
    except Exception as e:
        print(f"❌ Error retrieving logs from Coralogix: {e}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []


def generate_coralogix_ui_link(crash_info: Dict[str, Any], logs_limit: int = 50) -> Optional[str]:
    """
    Generate a Coralogix UI link for viewing logs in the web interface.
    """
    try:
        # Get Coralogix configuration from environment
        account = os.environ.get('CORALOGIX_ACCOUNT')
        region = os.environ.get('CORALOGIX_REGION')
        
        if not account or not region:
            print("❌ Coralogix account or region not configured for UI link generation")
            return None
        
        task_arn = crash_info.get('task_arn', '')
        if not task_arn:
            print("❌ No task ARN available for UI link generation")
            return None
        
        # Build the DataPrime query (same as API query)
        query = f"source logs  | filter $l.subsystemname ~ '{crash_info['service_name']}' | filter $d.ecs_task_arn ~ '{task_arn}' | limit {logs_limit}"
        
        # URL encode the query
        encoded_query = urllib.parse.quote(query)
        
        # Build the Coralogix UI URL
        base_url = f"https://{account}.app.{region}.coralogix.com"
        ui_link = f"{base_url}/#/query-new/archive-logs?time=from:now-1h,to:now&querySyntax=dataprime&query={encoded_query}"
        
        print(f"🔗 Generated Coralogix UI link: {ui_link}")
        return ui_link
        
    except Exception as e:
        print(f"❌ Error generating Coralogix UI link: {e}")
        return None


def is_coralogix_enabled() -> bool:
    """Check if Coralogix integration is enabled and properly configured."""
    api_key = os.environ.get('CORALOGIX_API_KEY')
    region = os.environ.get('CORALOGIX_REGION')
    account = os.environ.get('CORALOGIX_ACCOUNT')
    enabled = os.environ.get('ENABLE_CORALOGIX_INTEGRATION', '').lower() == 'true'
    
    print(f"🐛 DEBUG Coralogix config: enabled={enabled}, api_key={'SET' if api_key else 'NOT SET'}, region={region}, account={account}")
    
    return enabled and bool(api_key and region and account)


def detect_log_destination(crash_info: Dict[str, Any]) -> str:
    """
    Detect whether logs should be retrieved from CloudWatch or Coralogix.
    Returns 'coralogix', 'cloudwatch', or 'none'.
    """
    # If Coralogix is enabled and configured, prefer it
    if is_coralogix_enabled():
        print("🎯 Coralogix integration is enabled and configured")
        return 'coralogix'
    
    # Fall back to CloudWatch detection logic
    from ecs_utils import get_log_configuration_from_task_def
    log_config = get_log_configuration_from_task_def(crash_info)
    
    if log_config and log_config.get('awslogs-group'):
        print("🎯 CloudWatch logs detected in task definition")
        return 'cloudwatch'
    
    print("🎯 No log destination detected")
    return 'none'