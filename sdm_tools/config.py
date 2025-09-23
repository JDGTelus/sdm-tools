"""Env-based config"""
import os


JIRA_URL = os.getenv('JIRA_URL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JQL_QUERY = os.getenv('JQL_QUERY')
DISPLAY_COLUMNS = os.getenv('DISPLAY_COLUMNS', 'id,summary,status').split(',')
DB_NAME = os.getenv('DB_NAME', 'data/sdm_tools.db')
TABLE_NAME = os.getenv('TABLE_NAME', 'iotmi_3p_issues')
REPO_PATH = os.getenv('REPO_PATH')
SIMPLE_STATS = os.getenv(
    'SIMPLE_STATS', 'ux/web/data/team_simple_stats.json')
BASIC_STATS = os.getenv(
    'BASIC_STATS', 'ux/web/data/team_basic_stats.json')
EXCLUDED_EMAILS = os.getenv('EXCLUDED_EMAILS', '').split(
    ',') if os.getenv('EXCLUDED_EMAILS') else []
