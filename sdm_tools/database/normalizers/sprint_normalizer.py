"""Sprint normalization for normalized database."""

from datetime import datetime, date
from rich.console import Console
from ...config import TABLE_NAME
from ...utils import parse_jira_date_to_local, get_local_timezone

console = Console()


def normalize_sprints(old_conn):
    """Extract and normalize sprint data.
    
    Args:
        old_conn: Connection to old database
    
    Returns:
        List of sprint dicts ready for insertion
    """
    cursor = old_conn.cursor()
    sprints = []
    
    sprint_table = f"{TABLE_NAME}_sprints"
    
    # Check if sprint table exists
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{sprint_table}'")
    if not cursor.fetchone():
        console.print(f"[bold yellow]No sprint table found: {sprint_table}[/bold yellow]")
        return sprints
    
    cursor.execute(f"SELECT id, name, state, startDate, endDate, boardId, goal FROM {sprint_table}")
    
    tz = get_local_timezone()
    
    for row in cursor.fetchall():
        sprint_id, name, state, start_date, end_date, board_id, goal = row
        
        # Parse ISO dates to local dates
        start_dt = parse_jira_date_to_local(start_date, tz) if start_date else None
        end_dt = parse_jira_date_to_local(end_date, tz) if end_date else None
        
        start_date_local = start_dt.date() if start_dt else None
        end_date_local = end_dt.date() if end_dt else None
        
        sprints.append({
            'id': sprint_id,
            'name': name,
            'state': state,
            'start_date': start_date,
            'end_date': end_date,
            'start_date_local': start_date_local.isoformat() if start_date_local else None,
            'end_date_local': end_date_local.isoformat() if end_date_local else None,
            'board_id': board_id,
            'goal': goal
        })
    
    console.print(f"[bold cyan]Extracted {len(sprints)} sprints[/bold cyan]")
    return sprints


def populate_sprints_table(conn, sprints_data):
    """Populate the sprints table.
    
    Args:
        conn: Database connection
        sprints_data: List of sprint dicts
    
    Returns:
        Dict mapping sprint dates to sprint_id for fast lookup
    """
    cursor = conn.cursor()
    sprint_date_map = []
    
    for sprint in sprints_data:
        cursor.execute("""
            INSERT INTO sprints (id, name, state, start_date, end_date, start_date_local, end_date_local, board_id, goal)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            sprint['id'],
            sprint['name'],
            sprint['state'],
            sprint['start_date'],
            sprint['end_date'],
            sprint['start_date_local'],
            sprint['end_date_local'],
            sprint['board_id'],
            sprint['goal']
        ))
        
        # Build date range map for sprint assignment
        if sprint['start_date_local'] and sprint['end_date_local']:
            sprint_date_map.append({
                'id': sprint['id'],
                'start': datetime.fromisoformat(sprint['start_date_local']).date(),
                'end': datetime.fromisoformat(sprint['end_date_local']).date()
            })
    
    conn.commit()
    console.print(f"[bold green]✓ Populated {len(sprints_data)} sprints[/bold green]")
    
    return sprint_date_map


def find_sprint_for_date(event_date, sprint_date_map):
    """Find which sprint was active on a given date.
    
    Args:
        event_date: date object
        sprint_date_map: List of {id, start, end} dicts
    
    Returns:
        sprint_id or None
    """
    if not isinstance(event_date, date):
        return None
    
    for sprint in sprint_date_map:
        if sprint['start'] <= event_date <= sprint['end']:
            return sprint['id']
    
    return None
