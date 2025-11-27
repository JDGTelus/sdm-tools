"""Database module for SDM Tools."""

from .commits import (
    create_git_commits_table,
    display_commits,
    store_commits_in_db,
    update_git_commits,
)
from .core import backup_table, create_table, execute_sql
from .issues import display_issues, store_issues_in_db
from .normalizers import normalize_all_data
from .refresh import (
    backup_database,
    get_active_developers,
    get_available_sprints,
    refresh_database_workflow,
)
from .reports import (
    generate_multi_sprint_report_json,
    generate_sprint_report_json,
    query_daily_activity,
    query_date_range_activity,
    query_multi_sprint_activity,
    query_sprint_activity,
)
from .schema import create_normalized_schema, drop_all_tables, get_table_stats
from .sprints import display_sprints_table, process_sprints_from_issues
from .standalone import generate_all_standalone_reports, generate_standalone_report
from .stats import (
    display_daily_report_summary,
    generate_daily_report_json,
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
    # Normalization
    "normalize_all_data",
    "refresh_database_workflow",
    "backup_database",
    "get_available_sprints",
    "get_active_developers",
    "query_daily_activity",
    "query_sprint_activity",
    "query_date_range_activity",
    "query_multi_sprint_activity",
    "generate_sprint_report_json",
    "generate_multi_sprint_report_json",
    # Standalone report generation
    "generate_standalone_report",
    "generate_all_standalone_reports",
]
