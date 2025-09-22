"""
ECS utilities module for extracting and enriching crash information.
Handles all ECS-related API calls and data processing.
"""

import boto3
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Initialize ECS client
ecs_client = boto3.client('ecs')


def extract_crash_info(detail: Dict[str, Any]) -> Dict[str, Any]:
    """Extract basic crash information from EventBridge event"""
    
    # Parse cluster ARN to get cluster name
    cluster_arn = detail.get('clusterArn', '')
    cluster_name = cluster_arn.split('/')[-1] if cluster_arn else 'unknown'
    
    # Extract service name from group
    group = detail.get('group', '')
    service_name = group.replace('service:', '') if group.startswith('service:') else group
    
    # Get container exit codes and reasons
    containers = detail.get('containers', [])
    failed_container = None
    exit_code = None
    container_reason = None
    
    for container in containers:
        if container.get('exitCode', 0) != 0:
            failed_container = container
            exit_code = container.get('exitCode')
            container_reason = container.get('reason', '')
            break
    
    # For launch failures, there might not be any containers with exit codes
    # In this case, the task-level stoppedReason will contain the error
    if not failed_container and containers:
        # Take the first container for context, even if it didn't fail
        failed_container = containers[0]
        # Look for container-level reason even without exit code
        container_reason = failed_container.get('reason', '')
    
    # Extract task definition version from ARN
    task_definition_arn = detail.get('taskDefinitionArn', '')
    task_def_version = 'N/A'
    if task_definition_arn:
        # Extract version from ARN like: arn:aws:ecs:region:account:task-definition/family:revision
        task_def_version = task_definition_arn.split(':')[-1]

    
    return {
        'timestamp': detail.get('createdAt', datetime.now(timezone.utc).isoformat()),
        'started_at': detail.get('startedAt', ''),
        'cluster_name': cluster_name,
        'cluster_arn': cluster_arn,
        'service_name': service_name,
        'task_arn': detail.get('taskArn', ''),
        'task_definition_arn': task_definition_arn,
        'task_definition_version': task_def_version,
        'stopped_reason': detail.get('stoppedReason', ''),
        'stop_code': detail.get('stopCode', ''),
        'exit_code': exit_code,
        'container_reason': container_reason,
        'failed_container': failed_container,
        'last_status': detail.get('lastStatus', ''),
        'desired_status': detail.get('desiredStatus', '')
    }


def enrich_crash_data(crash_info: Dict[str, Any]) -> Dict[str, Any]:
    """Enrich crash data with additional AWS API calls"""
    
    enriched = crash_info.copy()
    
    try:
        print(f"Enriching crash data for task: {crash_info.get('task_arn', 'unknown')}")
        
        # Skip service details collection - not needed for notifications
        
        # Get recent logs from the failed container (if available)
        if crash_info['failed_container']:
            print(f"Getting logs for container: {crash_info['failed_container'].get('name', 'unknown')}")
            # Import here to avoid circular imports
            from logs_utils import get_recent_logs
            log_entries = get_recent_logs(crash_info)
            enriched['recent_logs'] = log_entries
            # Preserve the log_source that was set during log retrieval
            if 'log_source' in crash_info:
                enriched['log_source'] = crash_info['log_source']
                print(f"🐛 DEBUG: Preserved log_source in enriched data: {enriched['log_source']}")
            print(f"Enriched data now has {len(log_entries)} log entries")
        else:
            print("No container found for log retrieval")
            
        # Get task definition details
        if crash_info['task_definition_arn']:
            print(f"Getting task definition details")
            task_def_details = get_task_definition_details(crash_info['task_definition_arn'])
            enriched.update(task_def_details)
            
    except Exception as e:
        print(f"Error enriching crash data: {str(e)}")
        enriched['enrichment_error'] = str(e)
    
    return enriched


def get_task_definition_details(task_def_arn: str) -> Dict[str, Any]:
    """Get task definition details"""
    try:
        response = ecs_client.describe_task_definition(
            taskDefinition=task_def_arn
        )
        
        task_def = response.get('taskDefinition', {})
        return {
            'cpu': task_def.get('cpu'),
            'memory': task_def.get('memory'),
            'network_mode': task_def.get('networkMode'),
            'container_count': len(task_def.get('containerDefinitions', []))
        }
        
    except Exception as e:
        print(f"Error getting task definition details: {str(e)}")
    
    return {}


def get_log_configuration_from_task_def(crash_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get the actual log configuration from the task definition"""
    try:
        task_def_arn = crash_info.get('task_definition_arn')
        if not task_def_arn:
            print("No task definition ARN found")
            return None
            
        print(f"Describing task definition: {task_def_arn}")
        response = ecs_client.describe_task_definition(
            taskDefinition=task_def_arn
        )
        
        task_def = response.get('taskDefinition', {})
        failed_container = crash_info.get('failed_container', {})
        container_name = failed_container.get('name', '') if failed_container else ''
        
        if not container_name:
            print("No container name found for log configuration lookup")
            return None
        
        print(f"Looking for container '{container_name}' in task definition")
        print(f"Available containers: {[c.get('name') for c in task_def.get('containerDefinitions', [])]}")
        
        # Find the specific container definition
        for container_def in task_def.get('containerDefinitions', []):
            if container_def.get('name') == container_name:
                log_config = container_def.get('logConfiguration', {})
                print(f"Found log configuration for {container_name}: {log_config}")
                
                if log_config.get('logDriver') == 'awslogs':
                    options = log_config.get('options', {})
                    print(f"awslogs options: {options}")
                    return options
                else:
                    print(f"Container {container_name} uses log driver: {log_config.get('logDriver', 'none')}")
                    return None
        
        print(f"Container '{container_name}' not found in task definition")
        return None
        
    except Exception as e:
        print(f"Error getting log configuration: {str(e)}")
        import traceback
        print(f"Full traceback: {traceback.format_exc()}")
        return None