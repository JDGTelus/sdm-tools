"""Normalizers package - converts raw data to normalized schema."""

from .email_normalizer import normalize_email, extract_developer_from_jira_json
from .developer_normalizer import (
    extract_developers_from_jira,
    extract_git_emails,
    merge_developer_data,
    populate_developers_table,
    find_developer_id_by_email,
)
from .sprint_normalizer import (
    normalize_sprints,
    populate_sprints_table,
    find_sprint_for_date,
)
from .issue_normalizer import (
    normalize_issues,
    link_issues_to_sprints,
)
from .jira_event_normalizer import extract_jira_events
from .git_event_normalizer import extract_git_events, materialize_daily_activity


# Main orchestration function
def normalize_all_data(old_db_path, new_db_path):
    """Main orchestration function to normalize all data.
    
    Process:
        1. Extract developers from Jira
        2. Match git authors to developers
        3. Populate developers table
        4. Normalize sprints
        5. Normalize issues
        6. Link issues to sprints
        7. Extract Jira events
        8. Extract Git events
        9. Materialize daily activity summary
    
    Args:
        old_db_path: Path to old denormalized database
        new_db_path: Path to new normalized database
    
    Returns:
        Dict with statistics about the normalization
    """
    import sqlite3
    from rich.console import Console
    from ..schema import get_table_stats
    
    console = Console()
    
    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]    DATA NORMALIZATION PROCESS[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")
    
    stats = {}
    
    # Connect to databases
    old_conn = sqlite3.connect(old_db_path)
    new_conn = sqlite3.connect(new_db_path)
    
    try:
        # Step 1: Extract and merge developers
        console.print("[bold]Step 1/9: Extracting developers...[/bold]")
        jira_devs = extract_developers_from_jira(old_conn)
        git_emails = extract_git_emails(old_conn)
        merged_devs = merge_developer_data(jira_devs, git_emails)
        stats['developers'] = len(merged_devs)
        
        # Step 2: Populate developers table
        console.print("\n[bold]Step 2/9: Populating developers table...[/bold]")
        email_to_id = populate_developers_table(new_conn, merged_devs)
        
        # Step 3: Normalize sprints
        console.print("\n[bold]Step 3/9: Normalizing sprints...[/bold]")
        sprints_data = normalize_sprints(old_conn)
        sprint_date_map = populate_sprints_table(new_conn, sprints_data)
        stats['sprints'] = len(sprints_data)
        
        # Step 4: Normalize issues
        console.print("\n[bold]Step 4/9: Normalizing issues...[/bold]")
        stats['issues'] = normalize_issues(old_conn, new_conn)
        
        # Step 5: Link issues to sprints
        console.print("\n[bold]Step 5/9: Linking issues to sprints...[/bold]")
        stats['issue_sprint_links'] = link_issues_to_sprints(old_conn, new_conn)
        
        # Step 6: Extract Jira events
        console.print("\n[bold]Step 6/9: Extracting Jira events...[/bold]")
        stats['jira_events'] = extract_jira_events(old_conn, new_conn, sprint_date_map)
        
        # Step 7: Extract Git events
        console.print("\n[bold]Step 7/9: Extracting Git events...[/bold]")
        stats['git_events'] = extract_git_events(old_conn, new_conn, sprint_date_map)
        
        # Step 8: Materialize daily activity
        console.print("\n[bold]Step 8/9: Materializing daily activity summary...[/bold]")
        stats['summary_rows'] = materialize_daily_activity(new_conn)
        
        # Step 9: Final statistics
        console.print("\n[bold]Step 9/9: Generating statistics...[/bold]")
        table_stats = get_table_stats(new_conn)
        
        console.print("\n[bold green]═══════════════════════════════════════════════[/bold green]")
        console.print("[bold green]    NORMALIZATION COMPLETE![/bold green]")
        console.print("[bold green]═══════════════════════════════════════════════[/bold green]\n")
        
        console.print("[bold cyan]Summary:[/bold cyan]")
        console.print(f"  Developers: {table_stats.get('developers', 0)}")
        console.print(f"  Sprints: {table_stats.get('sprints', 0)}")
        console.print(f"  Issues: {table_stats.get('issues', 0)}")
        console.print(f"  Jira Events: {table_stats.get('jira_events', 0)}")
        console.print(f"  Git Events: {table_stats.get('git_events', 0)}")
        console.print(f"  Daily Summary Rows: {table_stats.get('daily_activity_summary', 0)}")
        
        stats['table_stats'] = table_stats
        
    finally:
        old_conn.close()
        new_conn.close()
    
    return stats


__all__ = [
    # Email utilities
    "normalize_email",
    "extract_developer_from_jira_json",
    # Developer functions
    "extract_developers_from_jira",
    "extract_git_emails",
    "merge_developer_data",
    "populate_developers_table",
    "find_developer_id_by_email",
    # Sprint functions
    "normalize_sprints",
    "populate_sprints_table",
    "find_sprint_for_date",
    # Issue functions
    "normalize_issues",
    "link_issues_to_sprints",
    # Event extraction
    "extract_jira_events",
    "extract_git_events",
    "materialize_daily_activity",
    # Main orchestration
    "normalize_all_data",
]
