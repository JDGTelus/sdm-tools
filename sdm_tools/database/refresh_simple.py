"""Simplified refresh workflow with incremental updates."""

import os
import sqlite3

from rich.console import Console

from ..config import DB_NAME
from .ingest import (
    calculate_sprint_points,
    get_last_commit_hash,
    get_last_jira_sync_time,
    ingest_git_commit,
    ingest_jira_issue,
)
from .schema_simple import create_simple_schema, get_table_stats

console = Console()


def ensure_database_exists():
    """Ensure database exists with proper schema.

    If database doesn't exist, creates it with schema.
    If database exists, validates schema (creates tables if missing).

    Returns:
        SQLite connection object
    """
    db_dir = os.path.dirname(DB_NAME)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir)
        console.print(f"[dim]Created directory: {db_dir}[/dim]")

    db_exists = os.path.exists(DB_NAME)

    conn = sqlite3.connect(DB_NAME)

    if not db_exists:
        console.print(f"[yellow]Creating new database: {DB_NAME}[/yellow]")
        create_simple_schema(conn)
    else:
        # Validate schema exists
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='developers'")
        if not cursor.fetchone():
            console.print(
                "[yellow]Database exists but schema is missing. Creating schema...[/yellow]"
            )
            create_simple_schema(conn)

    return conn


def refresh_data(full_refresh=False):
    """Refresh data from Jira and Git (incremental or full).

    Args:
        full_refresh: If True, refetch all data. If False, only fetch new/updated data.

    Returns:
        Boolean indicating success
    """
    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print(
        f"[bold cyan]    DATA REFRESH ({'FULL' if full_refresh else 'INCREMENTAL'})[/bold cyan]"
    )
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")

    try:
        # Ensure database exists
        conn = ensure_database_exists()

        # Step 1: Fetch from Jira
        console.print("[bold yellow]Step 1/3: Fetching from Jira...[/bold yellow]")
        jira_count = fetch_jira_data(conn, full_refresh)
        console.print(f"[green]  ✓ Processed {jira_count} Jira events[/green]")

        # Step 2: Fetch from Git
        console.print("\n[bold yellow]Step 2/3: Fetching from Git...[/bold yellow]")
        git_count = fetch_git_data(conn, full_refresh)
        console.print(f"[green]  ✓ Processed {git_count} Git commits[/green]")

        # Step 3: Calculate sprint metrics
        console.print("\n[bold yellow]Step 3/3: Calculating sprint metrics...[/bold yellow]")
        calculate_sprint_points(conn)
        console.print("[green]  ✓ Sprint points calculated[/green]")

        # Display final statistics
        console.print("\n[bold green]═══════════════════════════════════════════════[/bold green]")
        console.print("[bold green]    REFRESH COMPLETE![/bold green]")
        console.print("[bold green]═══════════════════════════════════════════════[/bold green]\n")

        stats = get_table_stats(conn)
        console.print("[bold cyan]Database Statistics:[/bold cyan]")
        console.print(f"  Developers: {stats.get('developers', 0)}")
        console.print(f"  Sprints: {stats.get('sprints', 0)}")
        console.print(f"  Activity Events: {stats.get('activity_events', 0)}")

        conn.close()
        console.print()
        return True

    except Exception as e:
        console.print(f"\n[bold red]Error during refresh: {e}[/bold red]")
        import traceback

        traceback.print_exc()
        return False


def fetch_jira_data(conn, full_refresh=False):
    """Fetch data from Jira (incremental or full).

    Args:
        conn: SQLite connection
        full_refresh: If True, fetch all. If False, fetch only updated since last sync.

    Returns:
        Number of events processed
    """
    from ..config import JQL_QUERY
    from ..jira import fetch_issue_details, fetch_issue_ids

    # Determine JQL query based on refresh type
    if full_refresh:
        jql = JQL_QUERY
        console.print("[dim]  Fetching all issues (full refresh)...[/dim]")
    else:
        last_sync = get_last_jira_sync_time(conn)
        if last_sync:
            # Fetch only updated issues since last sync
            jql = f"{JQL_QUERY} AND updated >= '{last_sync}'"
            console.print(f"[dim]  Fetching issues updated since {last_sync}...[/dim]")
        else:
            # No previous sync, do full fetch
            jql = JQL_QUERY
            console.print("[dim]  No previous sync found. Fetching all issues...[/dim]")

    # Temporarily override JQL for fetch
    import sdm_tools.config as config

    original_jql = config.JQL_QUERY
    config.JQL_QUERY = jql

    try:
        issue_ids = fetch_issue_ids()

        if not issue_ids:
            console.print("[dim]  No issues to fetch[/dim]")
            return 0

        console.print(f"[dim]  Found {len(issue_ids)} issue(s) to process[/dim]")

        issues = fetch_issue_details(issue_ids)

        if not issues:
            console.print("[yellow]  Warning: Failed to fetch issue details[/yellow]")
            return 0

        # Ingest issues
        events_created = 0
        for issue in issues:
            count = ingest_jira_issue(conn, issue)
            events_created += count

        conn.commit()
        return events_created

    finally:
        # Restore original JQL
        config.JQL_QUERY = original_jql


def fetch_git_data(conn, full_refresh=False):
    """Fetch data from Git (incremental or full).

    Args:
        conn: SQLite connection
        full_refresh: If True, fetch all. If False, fetch only new commits.

    Returns:
        Number of commits processed
    """
    import subprocess

    from ..config import REPO_PATH

    if not REPO_PATH or not os.path.exists(REPO_PATH):
        console.print("[bold red]Repository path not configured or doesn't exist[/bold red]")
        return 0

    original_cwd = os.getcwd()
    os.chdir(REPO_PATH)

    try:
        if full_refresh:
            # Fetch all commits
            console.print("[dim]  Fetching all commits (full refresh)...[/dim]")
            cmd = ["git", "log", "--all", "--pretty=format:%H|%an|%ae|%aI|%s"]
        else:
            # Fetch only new commits
            last_hash = get_last_commit_hash(conn)
            if last_hash:
                console.print(f"[dim]  Fetching commits since {last_hash[:8]}...[/dim]")
                cmd = [
                    "git",
                    "log",
                    f"{last_hash}..HEAD",
                    "--all",
                    "--pretty=format:%H|%an|%ae|%aI|%s",
                ]
            else:
                console.print("[dim]  No previous commits found. Fetching all...[/dim]")
                cmd = ["git", "log", "--all", "--pretty=format:%H|%an|%ae|%aI|%s"]

        output = subprocess.check_output(cmd).decode("utf-8")
        commit_lines = output.strip().split("\n") if output.strip() else []

        if not commit_lines or not commit_lines[0]:
            console.print("[dim]  No new commits to process[/dim]")
            return 0

        console.print(f"[dim]  Found {len(commit_lines)} commit(s) to process[/dim]")

        # Parse and ingest commits
        commits_added = 0
        for line in commit_lines:
            if not line.strip():
                continue

            parts = line.split("|")
            if len(parts) >= 5:
                commit_data = {
                    "hash": parts[0],
                    "author": parts[1],
                    "email": parts[2],
                    "timestamp": parts[3],
                    "message": "|".join(parts[4:]),  # Rejoin in case message has |
                }

                if ingest_git_commit(conn, commit_data):
                    commits_added += 1

        conn.commit()
        return commits_added

    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Git command failed: {e}[/bold red]")
        return 0
    finally:
        os.chdir(original_cwd)


def get_database_info():
    """Get information about current database state.

    Returns:
        Dict with database info or None if doesn't exist
    """
    if not os.path.exists(DB_NAME):
        return None

    conn = sqlite3.connect(DB_NAME)
    stats = get_table_stats(conn)

    cursor = conn.cursor()

    # Get date range of events
    cursor.execute("SELECT MIN(event_date), MAX(event_date) FROM activity_events")
    date_range = cursor.fetchone()

    # Get last sync times
    last_jira = get_last_jira_sync_time(conn)
    last_commit = get_last_commit_hash(conn)

    conn.close()

    return {
        "stats": stats,
        "date_range": date_range,
        "last_jira_sync": last_jira,
        "last_commit_hash": last_commit[:8] if last_commit else None,
    }
