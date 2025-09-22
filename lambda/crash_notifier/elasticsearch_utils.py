"""
Elasticsearch utilities module for retrieving logs and generating UI links.
Handles all Elasticsearch API calls for log retrieval.
"""

import os
import json
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta


def get_elasticsearch_logs(crash_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Get recent logs from Elasticsearch using the Search API.
    Based on the proof of concept from build/elasticsearch.sh
    """
    try:
        # Get Elasticsearch configuration from environment
        endpoint = os.environ.get('ELASTICSEARCH_ENDPOINT')
        username = os.environ.get('ELASTICSEARCH_USERNAME')
        password = os.environ.get('ELASTICSEARCH_PASSWORD')
        index_pattern = os.environ.get('ELASTICSEARCH_INDEX_PATTERN', '*')
        
        if not endpoint or not username or not password:
            print("❌ Elasticsearch endpoint, username, or password not configured")
            return []
        
        task_arn = crash_info.get('task_arn')
        if not task_arn:
            print("❌ No task ARN available for Elasticsearch query")
            return []
        
        print(f"🔍 Retrieving logs from Elasticsearch for task: {task_arn}")
        
        crash_info['log_source'] = 'elasticsearch'
        
        # Build Elasticsearch search query similar to the shell script
        search_body = {
            "size": 50,  # Limit to 50 most recent logs
            "sort": [{"@timestamp": {"order": "desc"}}],
            "query": {
                "term": {
                    "ecs_task_arn": {
                        "value": task_arn
                    }
                }
            }
        }
        
        print(f"🔍 Elasticsearch query: {json.dumps(search_body, indent=2)}")
        
        # Make the API request
        url = f"{endpoint.rstrip('/')}/_search"
        auth = (username, password)
        headers = {'Content-Type': 'application/json'}
        
        print(f"📡 Making Elasticsearch API request to: {url}")
        
        response = requests.post(
            url,
            auth=auth,
            headers=headers,
            json=search_body,
            timeout=30
        )
        
        response.raise_for_status()
        result = response.json()
        
        # Extract log entries from the response
        log_entries = []
        hits = result.get('hits', {}).get('hits', [])
        
        for hit in hits:
            source = hit.get('_source', {})
            
            # Extract relevant fields similar to Coralogix format
            log_entry = {
                'timestamp': source.get('@timestamp', ''),
                'message': source.get('message', ''),
                'level': source.get('level', 'info'),
                'container_name': source.get('container_name', ''),
                'source': source.get('source', ''),
                'ecs_cluster': source.get('ecs_cluster', ''),
                'ecs_task_arn': source.get('ecs_task_arn', ''),
                'ecs_task_definition': source.get('ecs_task_definition', ''),
                'app_name': source.get('appName', ''),
                'environment': source.get('environment', ''),
                'version': source.get('version', ''),
                'category_name': source.get('categoryName', ''),
                'code': source.get('code', ''),
                # Include any other fields that might be useful
                'raw_log': source
            }
            
            log_entries.append(log_entry)
        
        print(f"🔄 Processed {len(log_entries)} log entries from Elasticsearch")
        
        # Store logs in crash_info for later use
        crash_info['recent_logs'] = log_entries
        crash_info['logs_count'] = len(log_entries)
        
        return log_entries
        
    except requests.RequestException as e:
        print(f"❌ Elasticsearch API request failed: {e}")
        return []
    except Exception as e:
        print(f"❌ Error retrieving logs from Elasticsearch: {e}")
        return []


def generate_elasticsearch_ui_link(crash_info: Dict[str, Any], logs_limit: int = 50) -> Optional[str]:
    """
    Generate a Kibana UI link for viewing logs in the web interface.
    Uses dedicated KIBANA_URL environment variable for the base URL.
    
    Generates URLs in the exact working format:
    https://kibana.com/app/discover#/?_g=(time:(from:now-1h,to:now))&_a=(query:(language:kuery,query:'ecs_task_arn:%22task-arn%22'))
    """
    try:
        import urllib.parse
        
        # Get Kibana configuration from environment
        kibana_url = os.environ.get('KIBANA_URL')
        
        if not kibana_url:
            print("❌ Kibana URL not configured for UI link generation")
            return None
        
        task_arn = crash_info.get('task_arn')
        if not task_arn:
            print("❌ No task ARN available for Kibana UI link")
            return None
        
        # Clean up the Kibana URL
        base_url = kibana_url.rstrip('/')
        
        # Create the exact format that works
        discover_path = "/app/discover"
        
        # URL encode the task ARN for the query
        encoded_task_arn = urllib.parse.quote(task_arn, safe='')
        
        # Build the URL in the exact working format
        g_param = "(time:(from:now-1h,to:now))"
        a_param = f"(query:(language:kuery,query:'ecs_task_arn:%22{encoded_task_arn}%22'))"
        
        # Build the final URL
        ui_link = f"{base_url}{discover_path}#/?_g={g_param}&_a={a_param}"
        
        print(f"📊 Generated working Kibana UI link: {ui_link}")
        return ui_link
        
    except Exception as e:
        print(f"❌ Error generating Kibana UI link: {e}")
        return None


def detect_log_destination(crash_info: Dict[str, Any]) -> str:
    """
    Detect whether to use Elasticsearch, Coralogix, or CloudWatch for log retrieval.
    Enhanced version that includes Elasticsearch detection.
    """
    # Check if Elasticsearch integration is enabled and configured
    elasticsearch_enabled = os.environ.get('ENABLE_ELASTICSEARCH_INTEGRATION', 'false').lower() == 'true'
    elasticsearch_endpoint = os.environ.get('ELASTICSEARCH_ENDPOINT')
    elasticsearch_username = os.environ.get('ELASTICSEARCH_USERNAME')
    elasticsearch_password = os.environ.get('ELASTICSEARCH_PASSWORD')
    
    if elasticsearch_enabled and elasticsearch_endpoint and elasticsearch_username and elasticsearch_password:
        print("🔍 Elasticsearch integration is enabled and configured")
        return 'elasticsearch'
    
    # Check if Coralogix integration is enabled and configured
    coralogix_enabled = os.environ.get('ENABLE_CORALOGIX_INTEGRATION', 'false').lower() == 'true'
    coralogix_api_key = os.environ.get('CORALOGIX_API_KEY')
    coralogix_region = os.environ.get('CORALOGIX_REGION')
    
    if coralogix_enabled and coralogix_api_key and coralogix_region:
        print("🔍 Coralogix integration is enabled and configured")
        return 'coralogix'
    
    # Default to CloudWatch
    print("🔍 Using CloudWatch for log retrieval")
    return 'cloudwatch'