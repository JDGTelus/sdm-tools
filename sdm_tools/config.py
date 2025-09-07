"""Env-based config"""
import os


JIRA_URL = os.getenv('JIRA_URL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JQL_QUERY = os.getenv('JQL_QUERY', 'project = "SET" AND component = "IOTMI 3P Connector"')
DISPLAY_COLUMNS = os.getenv('DISPLAY_COLUMNS', 'key,summary,assignee,status').split(',')
DB_NAME = os.getenv('DB_NAME', 'sdm_tools.db')
TABLE_NAME = os.getenv('TABLE_NAME', 'iotmi_3p_issues')
REPO_PATH = os.getenv('REPO_PATH')
REPO_NAME = os.getenv('REPO_NAME')
