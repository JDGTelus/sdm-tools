"""Git event extraction for normalized database."""

from rich.console import Console
from ...utils import parse_git_date_to_local, get_time_bucket, get_local_timezone
from .developer_normalizer import find_developer_id_by_email
from .sprint_normalizer import find_sprint_for_date

console = Console()


def extract_git_events(old_conn, new_conn, sprint_date_map):
    """Extract Git commit events from git_commits table.
    
    Args:
        old_conn: Connection to old database
        new_conn: Connection to new normalized database
        sprint_date_map: List of sprint date ranges
    
    Returns:
        Count of events created
    """
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()
    
    # Check if git_commits table exists
    old_cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'")
    if not old_cursor.fetchone():
        console.print("[bold yellow]No git_commits table found[/bold yellow]")
        return 0
    
    old_cursor.execute("SELECT hash, author_email, date, message FROM git_commits")
    
    tz = get_local_timezone()
    count = 0
    skipped = 0
    
    for row in old_cursor.fetchall():
        commit_hash, author_email, commit_date_str, message = row
        
        if not author_email or not commit_date_str:
            continue
        
        # Find developer ID
        developer_id = find_developer_id_by_email(new_conn, author_email)
        
        if not developer_id:
            skipped += 1
            continue
        
        # Parse git date
        commit_dt = parse_git_date_to_local(commit_date_str, tz)
        if not commit_dt:
            continue
        
        commit_date = commit_dt.date()
        commit_hour = commit_dt.hour
        time_bucket = get_time_bucket(commit_dt)
        sprint_id = find_sprint_for_date(commit_date, sprint_date_map)
        
        # Insert git event
        new_cursor.execute("""
            INSERT INTO git_events (
                developer_id, commit_hash, commit_timestamp, commit_date,
                commit_hour, time_bucket, sprint_id, message
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            developer_id, commit_hash, commit_date_str, commit_date.isoformat(),
            commit_hour, time_bucket, sprint_id, message
        ))
        count += 1
    
    new_conn.commit()
    console.print(f"[bold green]✓ Extracted {count} Git events[/bold green]")
    if skipped > 0:
        console.print(f"[yellow]  (Skipped {skipped} commits from developers not in INCLUDED_EMAILS)[/yellow]")
    
    return count


def materialize_daily_activity(conn):
    """Pre-aggregate all events into daily_activity_summary table.
    
    This creates a materialized view that combines Jira and Git events
    by date, developer, and time bucket for fast dashboard queries.
    
    Args:
        conn: Database connection
    
    Returns:
        Count of summary rows created
    """
    cursor = conn.cursor()
    
    console.print("[bold yellow]Materializing daily activity summary...[/bold yellow]")
    
    # Clear existing summary
    cursor.execute("DELETE FROM daily_activity_summary")
    
    # Aggregate Jira events
    cursor.execute("""
        INSERT INTO daily_activity_summary 
            (activity_date, developer_id, sprint_id, time_bucket, jira_count, git_count, total_count)
        SELECT 
            event_date,
            developer_id,
            sprint_id,
            time_bucket,
            COUNT(*) as jira_count,
            0 as git_count,
            COUNT(*) as total_count
        FROM jira_events
        GROUP BY event_date, developer_id, time_bucket
    """)
    
    # Aggregate Git events (merge with existing Jira counts)
    cursor.execute("""
        INSERT INTO daily_activity_summary 
            (activity_date, developer_id, sprint_id, time_bucket, jira_count, git_count, total_count)
        SELECT 
            commit_date,
            developer_id,
            sprint_id,
            time_bucket,
            0 as jira_count,
            COUNT(*) as git_count,
            COUNT(*) as total_count
        FROM git_events
        GROUP BY commit_date, developer_id, time_bucket
        ON CONFLICT(activity_date, developer_id, time_bucket) DO UPDATE SET
            git_count = git_count + excluded.git_count,
            total_count = total_count + excluded.total_count
    """)
    
    # Get count
    cursor.execute("SELECT COUNT(*) FROM daily_activity_summary")
    count = cursor.fetchone()[0]
    
    conn.commit()
    console.print(f"[bold green]✓ Materialized {count} daily activity summary rows[/bold green]")
    
    return count
