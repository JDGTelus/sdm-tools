"""Database refresh workflow - orchestrates full data refresh with normalization."""

import os
import shutil
import sqlite3
from datetime import datetime

from rich.console import Console

from ..config import DB_NAME
from .core import get_db_connection
from .normalizers import normalize_all_data
from .schema import create_normalized_schema, drop_all_tables, get_table_stats

console = Console()


def backup_database(keep_last=5):
    """Create timestamped backup of current database.

    Args:
        keep_last: Number of recent backups to keep (default: 5)

    Returns:
        Path to backup file or None if no database exists
    """
    if not os.path.exists(DB_NAME):
        console.print("[yellow]No database to backup[/yellow]")
        return None

    # Create backup with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.dirname(DB_NAME)
    backup_name = f"sdm_tools_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_name)

    try:
        shutil.copy2(DB_NAME, backup_path)
        file_size = os.path.getsize(backup_path)
        size_mb = file_size / (1024 * 1024)

        console.print(f"[bold green]✓ Database backed up: {backup_path}[/bold green]")
        console.print(f"[dim]  Size: {size_mb:.2f} MB[/dim]")

        # Cleanup old backups
        cleanup_old_backups(backup_dir, keep_last)

        return backup_path

    except Exception as e:
        console.print(f"[bold red]Error creating backup: {e}[/bold red]")
        return None


def cleanup_old_backups(backup_dir, keep_last=5):
    """Remove old backup files, keeping only the most recent ones.

    Args:
        backup_dir: Directory containing backups
        keep_last: Number of backups to keep (default: 5)
    """
    import glob

    # Find all backup files
    pattern = os.path.join(backup_dir, "sdm_tools_backup_*.db")
    backups = sorted(glob.glob(pattern), reverse=True)

    # Remove old backups
    if len(backups) > keep_last:
        old_backups = backups[keep_last:]
        for backup in old_backups:
            try:
                os.remove(backup)
                console.print(f"[dim]  Removed old backup: {os.path.basename(backup)}[/dim]")
            except Exception as e:
                console.print(f"[yellow]  Warning: Could not remove {backup}: {e}[/yellow]")


def refresh_database_workflow():
    """Complete database refresh workflow.

    Process:
        1. Backup current database
        2. Fetch fresh data from Jira
        3. Fetch fresh data from Git
        4. Create temporary database for raw data
        5. Normalize data into production database
        6. Display statistics

    Returns:
        Boolean indicating success
    """
    from ..jira import fetch_issue_details, fetch_issue_ids
    from .commits import update_git_commits
    from .issues import store_issues_in_db
    from .sprints import process_sprints_from_issues

    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]    DATABASE REFRESH WORKFLOW[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")

    # Store original DB_NAME for restoration in case of error
    import sdm_tools.config as config

    original_db_name = config.DB_NAME

    try:
        # Step 1: Backup existing database
        console.print("[bold yellow]Step 1/6: Backing up current database...[/bold yellow]")
        backup_path = backup_database()

        # Step 2: Create temporary database for raw data
        console.print(
            "\n[bold yellow]Step 2/6: Creating temporary database for raw data...[/bold yellow]"
        )
        temp_db = "data/sdm_tools_temp.db"

        # Remove temp db if it exists
        if os.path.exists(temp_db):
            os.remove(temp_db)

        # Temporarily change DB_NAME to temp for fetching
        config.DB_NAME = temp_db

        # Step 3: Fetch fresh Jira data
        console.print("\n[bold yellow]Step 3/6: Fetching fresh data from Jira...[/bold yellow]")
        issue_ids = fetch_issue_ids()

        if not issue_ids:
            console.print(
                "[bold red]Failed to fetch issue IDs from Jira. Aborting refresh.[/bold red]"
            )
            config.DB_NAME = original_db_name
            return False

        jira_issues = fetch_issue_details(issue_ids)

        if not jira_issues:
            console.print(
                "[bold red]Failed to fetch issue details from Jira. Aborting refresh.[/bold red]"
            )
            config.DB_NAME = original_db_name
            return False

        store_issues_in_db(jira_issues)
        process_sprints_from_issues(silent=True)

        # Step 4: Fetch fresh Git data
        console.print("\n[bold yellow]Step 4/6: Fetching fresh data from Git...[/bold yellow]")
        update_git_commits()

        # Step 5: Normalize into production database
        console.print("\n[bold yellow]Step 5/6: Normalizing data...[/bold yellow]")

        # Restore original DB_NAME
        config.DB_NAME = original_db_name

        # Drop existing tables in production DB
        if os.path.exists(original_db_name):
            conn = sqlite3.connect(original_db_name)
            drop_all_tables(conn)
            conn.close()

        # Create fresh schema
        conn = sqlite3.connect(original_db_name)
        create_normalized_schema(conn)
        conn.close()

        # Run normalization from temp to production
        normalize_all_data(temp_db, original_db_name)

        # Step 6: Display final statistics
        console.print("\n[bold yellow]Step 6/6: Generating final statistics...[/bold yellow]")

        conn = sqlite3.connect(original_db_name)
        table_stats = get_table_stats(conn)
        conn.close()

        console.print("\n[bold green]═══════════════════════════════════════════════[/bold green]")
        console.print("[bold green]    DATABASE REFRESH COMPLETE![/bold green]")
        console.print("[bold green]═══════════════════════════════════════════════[/bold green]\n")

        console.print("[bold cyan]Final Statistics:[/bold cyan]")
        console.print(
            f"  Active Developers: {sum(1 for k, v in table_stats.items() if k == 'developers' for _ in range(v))}"
        )
        console.print(f"  Sprints: {table_stats.get('sprints', 0)}")
        console.print(f"  Issues: {table_stats.get('issues', 0)}")
        console.print(f"  Jira Events: {table_stats.get('jira_events', 0)}")
        console.print(f"  Git Events: {table_stats.get('git_events', 0)}")
        console.print(f"  Daily Summary Rows: {table_stats.get('daily_activity_summary', 0)}")

        if backup_path:
            console.print(f"\n[dim]Previous database backed up to: {backup_path}[/dim]")

        # Cleanup temp database
        if os.path.exists(temp_db):
            os.remove(temp_db)
            console.print("[dim]Cleaned up temporary database[/dim]")

        console.print()
        return True

    except Exception as e:
        console.print(f"\n[bold red]Error during refresh: {e}[/bold red]")
        import traceback

        traceback.print_exc()

        # Restore DB_NAME
        config.DB_NAME = original_db_name

        return False


def get_available_sprints():
    """Get list of available sprints from the database.

    Returns:
        List of tuples: (sprint_id, name, state, start_date, end_date)
    """
    if not os.path.exists(DB_NAME):
        return []

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, state, start_date_local, end_date_local
                FROM sprints
                ORDER BY start_date_local DESC
            """
            )
            sprints = cursor.fetchall()
            return sprints
    except:
        return []


def get_active_developers():
    """Get list of active developers from the database.

    Returns:
        List of tuples: (developer_id, name, email)
    """
    if not os.path.exists(DB_NAME):
        return []

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, email
                FROM developers
                WHERE active = 1
                ORDER BY name
            """
            )
            developers = cursor.fetchall()
            return developers
    except:
        return []
