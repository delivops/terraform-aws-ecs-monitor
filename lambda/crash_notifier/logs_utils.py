"""
CloudWatch Logs utilities module for retrieving container logs.
Handles all CloudWatch Logs API calls and log processing.
"""

import boto3
from typing import Dict, Any, List

# Initialize CloudWatch Logs client
logs_client = boto3.client('logs')


def get_recent_logs(crash_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get recent logs for the specific failed task from Coralogix or CloudWatch"""
    try:
        print(f"🐛 DEBUG: Starting get_recent_logs, initial log_source: {crash_info.get('log_source', 'NOT SET')}")
        
        failed_container = crash_info.get('failed_container')
        if not failed_container:
            print("No failed container found in crash info")
            return []
        
        # Import here to avoid circular imports
        from coralogix_utils import get_coralogix_logs
        from elasticsearch_utils import detect_log_destination, get_elasticsearch_logs
        
        # Detect whether to use Elasticsearch, Coralogix, or CloudWatch
        log_destination = detect_log_destination(crash_info)
        print(f"🐛 DEBUG: Detected log destination: {log_destination}")
        print(f"🐛 DEBUG: log_source before log retrieval attempt: {crash_info.get('log_source', 'NOT SET')}")
        
        if log_destination == 'elasticsearch':
            print("🔄 Using Elasticsearch for log retrieval")
            logs = get_elasticsearch_logs(crash_info)
            print(f"🐛 DEBUG: After Elasticsearch call, log_source: {crash_info.get('log_source', 'NOT SET')}")
            if logs:
                print(f"✅ Retrieved {len(logs)} log entries from Elasticsearch")
                crash_info['log_source'] = 'elasticsearch'  # Force set it again
                print(f"🐛 DEBUG: FORCED log_source to: {crash_info.get('log_source')}")
                return logs
            else:
                print("⚠️ No logs found in Elasticsearch, falling back to CloudWatch")
                # Fall through to CloudWatch
        
        if log_destination == 'coralogix':
            print("🔄 Using Coralogix for log retrieval")
            logs = get_coralogix_logs(crash_info)
            print(f"🐛 DEBUG: After Coralogix call, log_source: {crash_info.get('log_source', 'NOT SET')}")
            if logs:
                print(f"✅ Retrieved {len(logs)} log entries from Coralogix")
                crash_info['log_source'] = 'coralogix'  # Force set it again
                print(f"🐛 DEBUG: FORCED log_source to: {crash_info.get('log_source')}")
                return logs
            else:
                print("⚠️ No logs found in Coralogix, falling back to CloudWatch")
                # Fall through to CloudWatch
        
        if log_destination == 'cloudwatch' or log_destination in ['coralogix', 'elasticsearch']:
            print("🔄 Using CloudWatch for log retrieval")
            logs = get_cloudwatch_logs(crash_info)
            if logs and crash_info.get('log_source') not in ['coralogix', 'elasticsearch']:
                crash_info['log_source'] = 'cloudwatch'
                print(f"🐛 DEBUG: Set log_source to cloudwatch")
            print(f"🐛 DEBUG: Final log_source before return: {crash_info.get('log_source', 'NOT SET')}")
            return logs
        
        print("❌ No log destination available")
        return []
        
    except Exception as e:
        print(f"Error getting recent logs for task: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []


def get_cloudwatch_logs(crash_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get recent CloudWatch logs for the specific failed task using ONLY task definition"""
def get_cloudwatch_logs(crash_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Get recent CloudWatch logs for the specific failed task using ONLY task definition"""
    try:
        failed_container = crash_info.get('failed_container')
        if not failed_container:
            print("No failed container found in crash info")
            return []
            
        container_name = failed_container.get('name', '')
        task_arn = crash_info.get('task_arn', '')
        
        if not container_name or not task_arn:
            print(f"Missing container name ({container_name}) or task ARN ({task_arn})")
            return []
        
        # Extract task ID from task ARN
        task_id = task_arn.split('/')[-1] if task_arn else ''
        print(f"Looking for logs for task {task_id}, container {container_name}")
        
        # Get log configuration from task definition - ONLY authoritative source
        from ecs_utils import get_log_configuration_from_task_def
        log_config = get_log_configuration_from_task_def(crash_info)
        
        if log_config:
            print(f"SUCCESS: Found log config from task definition: {log_config}")
            logs = get_logs_with_config(crash_info, log_config, task_id)
            if logs:
                print(f"SUCCESS: Retrieved {len(logs)} log entries using task definition config")
                # Add metadata to indicate source
                crash_info['log_source'] = 'cloudwatch'
                return logs
            else:
                print("INFO: Task definition config is correct, but no logs found in time window (container may not have logged anything)")
                return []
        else:
            print("ERROR: No log config found in task definition - container not configured for CloudWatch logging")
            return []
        
    except Exception as e:
        print(f"Error getting CloudWatch logs for task: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []


def get_logs_with_config(crash_info: Dict[str, Any], log_config: Dict[str, Any], task_id: str) -> List[Dict[str, Any]]:
    """Get logs using the actual log configuration from task definition"""
    try:
        # Extract log group and stream prefix from actual config
        log_group = log_config.get('awslogs-group', '')
        stream_prefix = log_config.get('awslogs-stream-prefix', '')
        region = log_config.get('awslogs-region', '')
        
        print(f"Using EXACT log config from task definition:")
        print(f"  Log group: {log_group}")
        print(f"  Stream prefix: {stream_prefix}")
        print(f"  Region: {region}")
        
        if not log_group:
            print("ERROR: No log group specified in task definition!")
            return []
        
        # Build the actual log stream name according to ECS documentation
        failed_container = crash_info.get('failed_container', {})
        container_name = failed_container.get('name', '') if failed_container else ''
        
        if not container_name:
            print("ERROR: No container name available for log stream construction")
            return []
        
        # ECS log stream naming: [prefix/]container-name/task-id
        if stream_prefix:
            log_stream = f"{stream_prefix}/{container_name}/{task_id}"
        else:
            log_stream = f"{container_name}/{task_id}"
        
        print(f"Constructed log stream name: {log_stream}")
        
        # Verify the log stream exists before trying to get logs
        try:
            print(f"Verifying log stream exists in {log_group}...")
            response = logs_client.describe_log_streams(
                logGroupName=log_group,
                logStreamNamePrefix=log_stream,
                limit=1
            )
            
            if not response.get('logStreams'):
                print(f"ERROR: Log stream {log_stream} not found in {log_group}")
                # Try to find what streams DO exist for this task
                print(f"Searching for any streams containing task ID {task_id}...")
                response = logs_client.describe_log_streams(
                    logGroupName=log_group,
                    orderBy='LastEventTime',
                    descending=True,
                    limit=50
                )
                
                matching_streams = [s['logStreamName'] for s in response.get('logStreams', []) if task_id in s['logStreamName']]
                if matching_streams:
                    print(f"Found alternative streams with task ID: {matching_streams}")
                    # Use the first matching stream
                    log_stream = matching_streams[0]
                    print(f"Using stream: {log_stream}")
                else:
                    print(f"No streams found containing task ID {task_id} in log group {log_group}")
                    return []
            else:
                actual_stream = response['logStreams'][0]['logStreamName']
                print(f"Confirmed log stream exists: {actual_stream}")
                log_stream = actual_stream
        
        except Exception as verify_error:
            print(f"Error verifying log stream: {str(verify_error)}")
            return []
        
        return get_logs_from_stream(crash_info, log_group, log_stream)
        
    except Exception as e:
        print(f"Error getting logs with config: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []


def get_logs_from_stream(crash_info: Dict[str, Any], log_group: str, log_stream: str) -> List[Dict[str, Any]]:
    """Get ALL logs from a specific log group and stream - no time filtering"""
    try:
        print(f"Getting ALL logs from {log_group}/{log_stream}")
        
        # Just get ALL logs from this stream - no time filtering!
        response = logs_client.filter_log_events(
            logGroupName=log_group,
            logStreamNames=[log_stream],
            limit=100  # Get up to 100 log events
        )
        
        events = response.get('events', [])
        print(f"Found {len(events)} total log events in stream")
        
        if not events:
            print("No log events found in this stream")
            return []
        
        # Just return all the logs, sorted by timestamp
        log_entries = [
            {
                'timestamp': event['timestamp'],
                'message': event['message'].strip()
            }
            for event in events
        ]
        
        print(f"Returning {len(log_entries)} log entries (all logs from stream)")
        return log_entries
        
    except Exception as e:
        print(f"Error getting logs from stream {log_stream}: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return []