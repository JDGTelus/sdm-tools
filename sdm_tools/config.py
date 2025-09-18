"""Env-based config"""
import os


JIRA_URL = os.getenv('JIRA_URL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JQL_QUERY = os.getenv('JQL_QUERY')
DISPLAY_COLUMNS = os.getenv('DISPLAY_COLUMNS').split(',')
DB_NAME = os.getenv('DB_NAME')
TABLE_NAME = os.getenv('TABLE_NAME')
REPO_PATH = os.getenv('REPO_PATH')
STATS_FILENAME = os.getenv('STATS_FILENAME')
