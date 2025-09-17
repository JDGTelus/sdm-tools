"""Jira handler"""
import requests
from requests.auth import HTTPBasicAuth
from .config import JIRA_URL, JIRA_API_TOKEN, JIRA_EMAIL, JQL_QUERY
def fetch_issue_ids():
    """ Fetches all issue IDs from Jira using JQL with pagination. """
    url = f"{JIRA_URL}/rest/api/3/search/jql"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    all_issue_ids = []
    next_page_token = None
    max_results = 50  # Follow Jira recommendation of max 50 records per request
    while True:
        # Prepare request body according to current API spec
        request_body = {
            'jql': JQL_QUERY,
            'maxResults': max_results,
            'fields': ['id']  # Only fetch ID field for efficiency
        }
        # Add pagination token if available
        if next_page_token:
            request_body['nextPageToken'] = next_page_token
        response = requests.post(
            url,
            headers=headers,
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
            json=request_body
        )
        if response.status_code != 200:
            raise Exception(f"Failed to fetch issue IDs: {response.status_code} - {response.text}")
        response_data = response.json()
        issues = response_data.get('issues', [])
        # Add issue IDs from this batch
        all_issue_ids.extend([issue['id'] for issue in issues])
        # Check if this is the last page
        is_last = response_data.get('isLast', True)
        if is_last or len(issues) == 0:
            break
        # Get next page token for pagination
        next_page_token = response_data.get('nextPageToken')
        if not next_page_token:
            break
    return all_issue_ids
def fetch_issue_details(issue_ids):
    """ Fetches detailed issue data for given issue IDs with batching. """
    url = f"{JIRA_URL}/rest/api/3/issue/bulkfetch"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    all_issues = []
    batch_size = 100  # Maximum allowed by Jira API for bulk fetch
    # Process issue IDs in batches
    for i in range(0, len(issue_ids), batch_size):
        batch_ids = issue_ids[i:i + batch_size]
        data = {'issueIdsOrKeys': batch_ids, 'fields': ['*all']}
        response = requests.post(
            url,
            headers=headers,
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
            json=data
        )
        if response.status_code != 200:
            raise Exception(f"Failed to fetch issue details for batch {i//batch_size + 1}: {response.status_code} - {response.text}")
        batch_issues = response.json().get('issues', [])
        all_issues.extend(batch_issues)
    return all_issues