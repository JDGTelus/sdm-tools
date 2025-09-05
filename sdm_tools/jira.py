"""Jira handler"""
import requests
from requests.auth import HTTPBasicAuth
from .config import JIRA_URL, JIRA_API_TOKEN, JIRA_EMAIL, JQL_QUERY


def fetch_issue_ids():
    """ Fetches issue IDs from Jira using JQL. """
    url = f"{JIRA_URL}/rest/api/3/search/jql"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    params = {'jql': JQL_QUERY, 'maxResults': 50}

    response = requests.post(
        url,
        headers=headers,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
        json=params
    )

    if response.status_code != 200:
        raise Exception(f"Failed to fetch issue IDs: {response.status_code} - {response.text}")

    return [issue['id'] for issue in response.json().get('issues', [])]


def fetch_issue_details(issue_ids):
    """ Fetches detailed issue data for given issue IDs. """
    url = f"{JIRA_URL}/rest/api/3/issue/bulkfetch"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    data = {'issueIdsOrKeys': issue_ids, 'fields': ['*all']}

    response = requests.post(
        url,
        headers=headers,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
        json=data
    )

    if response.status_code != 200:
        raise Exception(f"Failed to fetch issue details: {response.status_code} - {response.text}")

    return response.json().get('issues', [])
