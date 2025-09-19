"""Env-based config"""
import os


JIRA_URL = os.getenv('JIRA_URL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JQL_QUERY = os.getenv('JQL_QUERY')
DISPLAY_COLUMNS = os.getenv('DISPLAY_COLUMNS', 'id,summary,status').split(',')
DB_NAME = os.getenv('DB_NAME', 'sdm_tools.db')
TABLE_NAME = os.getenv('TABLE_NAME', 'issues')
REPO_PATH = os.getenv('REPO_PATH')
STATS_FILENAME = os.getenv('STATS_FILENAME', 'team_simple_stats.json')
BASIC_FILENAME = os.getenv('BASIC_FILENAME', 'team_basic_stats.json')
EXCLUDED_EMAILS = os.getenv('EXCLUDED_EMAILS', '').split(
    ',') if os.getenv('EXCLUDED_EMAILS') else []

# Legacy support
BASIC_STATS = BASIC_FILENAME
