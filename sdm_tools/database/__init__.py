"""Database module for SDM Tools."""

from .core import execute_sql, backup_table, create_table
from .issues import store_issues_in_db, display_issues
from .commits import (
    update_git_commits,
    display_commits,
    store_commits_in_db,
    create_git_commits_table,
)
from .stats import (
    generate_daily_report_json,
    display_daily_report_summary,
)
from .sprints import process_sprints_from_issues, display_sprints_table
from .schema import create_normalized_schema, drop_all_tables, get_table_stats
from .normalize import normalize_all_data
from .refresh import (
    refresh_database_workflow,
    backup_database,
    get_available_sprints,
    get_active_developers,
)
from .reports import (
    query_daily_activity,
    query_sprint_activity,
    query_date_range_activity,
    generate_sprint_report_json,
)

__all__ = [
    "execute_sql",
    "backup_table",
    "create_table",
    "store_issues_in_db",
    "display_issues",
    "update_git_commits",
    "display_commits",
    "store_commits_in_db",
    "create_git_commits_table",
    "generate_daily_report_json",
    "display_daily_report_summary",
    "process_sprints_from_issues",
    "display_sprints_table",
    # New normalized database functions
    "create_normalized_schema",
    "drop_all_tables",
    "get_table_stats",
    "normalize_all_data",
    "refresh_database_workflow",
    "backup_database",
    "get_available_sprints",
    "get_active_developers",
    "query_daily_activity",
    "query_sprint_activity",
    "query_date_range_activity",
    "generate_sprint_report_json",
]
