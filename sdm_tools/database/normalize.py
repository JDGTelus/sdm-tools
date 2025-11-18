"""Data normalization module for transforming raw Jira/Git data into normalized tables."""

import re
import sqlite3
from datetime import datetime, date
from collections import defaultdict
from rich.console import Console
from ..config import DB_NAME, TABLE_NAME, INCLUDED_EMAILS
from ..utils import (
    parse_jira_date_to_local,
    parse_git_date_to_local,
    get_time_bucket,
    get_local_timezone
)

console = Console()


# ============================================================================
# EMAIL NORMALIZATION AND MATCHING
# ============================================================================

def normalize_email(email):
    """Normalize email to canonical form with auto-mapping patterns.
    
    Handles:
        - AWS SSO prefixes: AWSReservedSSO_xxx/user@domain.com -> user@domain.com
        - Case sensitivity: User@Domain.com -> user@domain.com
        - Domain variations: @telusinternational.com -> @telus.com
        - Numeric suffixes: carlos.carias01@telus.com -> carlos.carias@telus.com
    
    Args:
        email: Raw email string
    
    Returns:
        Normalized email string or None
    """
    if not email or email == 'Unknown':
        return None
    
    # 1. Strip whitespace
    email = email.strip()
    
    # 2. Remove AWS SSO prefix
    # Pattern: "AWSReservedSSO_TELUS-IoT-Developer_xxx/user@domain.com"
    if '/' in email and email.startswith('AWSReservedSSO'):
        email = email.split('/')[-1]
    
    # 3. Lowercase
    email = email.lower()
    
    # 4. Domain normalization - map telusinternational.com to telus.com
    email = email.replace('@telusinternational.com', '@telus.com')
    
    # 5. Remove numeric suffixes before @ (e.g., carlos.carias01 -> carlos.carias)
    # Only remove trailing digits in the local part
    email = re.sub(r'(\d+)@', '@', email)
    
    return email


def extract_developer_from_jira_json(jira_json_str):
    """Extract developer info from Jira assignee/creator/reporter JSON string.
    
    Args:
        jira_json_str: JSON string like "{'emailAddress': '...', 'displayName': '...'}"
    
    Returns:
        Tuple of (normalized_email, display_name, account_id) or (None, None, None)
    """
    if not jira_json_str:
        return None, None, None
    
    try:
        import ast
        data = ast.literal_eval(jira_json_str)
        
        raw_email = data.get('emailAddress', '')
        email = normalize_email(raw_email)
        name = data.get('displayName', '')
        account_id = data.get('accountId', '')
        
        return email, name, account_id
    except Exception as e:
        # console.print(f"[dim yellow]Warning: Could not parse Jira JSON: {str(e)}[/dim yellow]")
        return None, None, None


# ============================================================================
# DEVELOPER TABLE POPULATION
# ============================================================================

def extract_developers_from_jira(old_conn):
    """Extract unique developers from Jira issues table.
    
    Extracts from:
        - assignee
        - creator
        - reporter
    
    Args:
        old_conn: Connection to old database with iotmi_3p_issues table
    
    Returns:
        Dict of {email: {'name': name, 'account_id': account_id, 'aliases': [emails]}}
    """
    cursor = old_conn.cursor()
    developers = {}
    
    # Check if table exists
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
    if not cursor.fetchone():
        console.print(f"[bold red]Table {TABLE_NAME} not found in old database[/bold red]")
        return developers
    
    # Get table columns
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]
    
    # Extract from assignee, creator, reporter
    for field in ['assignee', 'creator', 'reporter']:
        if field not in columns:
            continue
        
        cursor.execute(f"SELECT DISTINCT {field} FROM {TABLE_NAME} WHERE {field} IS NOT NULL AND {field} != ''")
        
        for row in cursor.fetchall():
            jira_json = row[0]
            email, name, account_id = extract_developer_from_jira_json(jira_json)
            
            if email:
                if email not in developers:
                    developers[email] = {
                        'name': name,
                        'account_id': account_id,
                        'aliases': set()
                    }
                # Always update name if we have a better one (longer, more complete)
                if name and len(name) > len(developers[email]['name']):
                    developers[email]['name'] = name
    
    console.print(f"[bold cyan]Extracted {len(developers)} unique developers from Jira[/bold cyan]")
    return developers


def extract_git_emails(old_conn):
    """Extract all unique git author emails from git_commits table.
    
    Args:
        old_conn: Connection to old database with git_commits table
    
    Returns:
        Dict of {normalized_email: [raw_email_variations]}
    """
    cursor = old_conn.cursor()
    git_emails = defaultdict(list)
    
    # Check if git_commits table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'")
    if not cursor.fetchone():
        console.print("[bold yellow]No git_commits table found[/bold yellow]")
        return git_emails
    
    cursor.execute("SELECT DISTINCT author_email FROM git_commits WHERE author_email IS NOT NULL")
    
    for row in cursor.fetchall():
        raw_email = row[0]
        normalized = normalize_email(raw_email)
        
        if normalized:
            git_emails[normalized].append(raw_email)
    
    console.print(f"[bold cyan]Extracted {len(git_emails)} unique git author emails[/bold cyan]")
    return git_emails


def merge_developer_data(jira_devs, git_emails):
    """Merge Jira developers with Git email variations.
    
    Args:
        jira_devs: Dict from extract_developers_from_jira()
        git_emails: Dict from extract_git_emails()
    
    Returns:
        Merged dict with git email aliases added
    """
    # Add git email variations as aliases
    for normalized_email, raw_variations in git_emails.items():
        if normalized_email in jira_devs:
            jira_devs[normalized_email]['aliases'].update(raw_variations)
        else:
            # Git-only developer (no Jira presence)
            # Extract name from email
            name = normalized_email.split('@')[0].replace('.', ' ').title()
            jira_devs[normalized_email] = {
                'name': name,
                'account_id': '',
                'aliases': set(raw_variations)
            }
    
    return jira_devs


def populate_developers_table(conn, developers_data):
    """Populate the developers and developer_email_aliases tables.
    
    Args:
        conn: Connection to new normalized database
        developers_data: Dict from merge_developer_data()
    
    Returns:
        Dict mapping {email: developer_id}
    """
    cursor = conn.cursor()
    email_to_id = {}
    
    # Filter to only included developers if INCLUDED_EMAILS is configured
    included_emails_set = set(e.strip().lower() for e in INCLUDED_EMAILS if e.strip())
    
    for email, data in developers_data.items():
        # Determine if developer is active (in INCLUDED_EMAILS or no filter configured)
        if included_emails_set:
            active = email in included_emails_set
        else:
            active = True  # No filter = all active
        
        # Insert developer
        cursor.execute("""
            INSERT INTO developers (email, name, jira_account_id, active)
            VALUES (?, ?, ?, ?)
        """, (email, data['name'], data['account_id'], active))
        
        developer_id = cursor.lastrowid
        email_to_id[email] = developer_id
        
        # Insert email aliases
        for alias in data['aliases']:
            if alias != email:  # Don't duplicate the primary email
                cursor.execute("""
                    INSERT OR IGNORE INTO developer_email_aliases (developer_id, alias_email, source)
                    VALUES (?, ?, 'git')
                """, (developer_id, alias.lower(), ))
    
    conn.commit()
    
    active_count = sum(1 for d in developers_data.values() if d.get('active', True))
    console.print(f"[bold green]✓ Populated {len(email_to_id)} developers ({active_count} active)[/bold green]")
    
    return email_to_id


def find_developer_id_by_email(conn, raw_email):
    """Find developer ID by matching email (including aliases).
    
    Args:
        conn: Database connection
        raw_email: Raw email to match
    
    Returns:
        developer_id or None
    """
    if not raw_email:
        return None
    
    normalized = normalize_email(raw_email)
    if not normalized:
        return None
    
    cursor = conn.cursor()
    
    # Try exact match on primary email
    cursor.execute("SELECT id FROM developers WHERE email = ?", (normalized,))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    # Try match on aliases
    cursor.execute("""
        SELECT developer_id FROM developer_email_aliases WHERE alias_email = ?
    """, (normalized,))
    result = cursor.fetchone()
    if result:
        return result[0]
    
    return None


# ============================================================================
# SPRINT NORMALIZATION
# ============================================================================

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


# ============================================================================
# ISSUES NORMALIZATION
# ============================================================================

def normalize_issues(old_conn, new_conn):
    """Extract and normalize issue data.
    
    Args:
        old_conn: Connection to old database
        new_conn: Connection to new normalized database
    
    Returns:
        Count of issues processed
    """
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()
    
    # Check if table exists
    old_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
    if not old_cursor.fetchone():
        console.print(f"[bold red]Table {TABLE_NAME} not found[/bold red]")
        return 0
    
    # Get table columns
    old_cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in old_cursor.fetchall()]
    
    # Build SELECT query for available fields
    fields = ['id', 'summary', 'status', 'assignee', 'creator', 'created', 'updated']
    if 'statuscategorychangedate' in columns:
        fields.append('statuscategorychangedate')
    
    query = f"SELECT {', '.join(fields)} FROM {TABLE_NAME}"
    old_cursor.execute(query)
    
    tz = get_local_timezone()
    count = 0
    
    for row in old_cursor.fetchall():
        issue_id = row[0]
        summary = row[1] if len(row) > 1 else None
        status_json = row[2] if len(row) > 2 else None
        assignee_json = row[3] if len(row) > 3 else None
        creator_json = row[4] if len(row) > 4 else None
        created = row[5] if len(row) > 5 else None
        updated = row[6] if len(row) > 6 else None
        status_changed = row[7] if len(row) > 7 and 'statuscategorychangedate' in columns else None
        
        # Extract status name from JSON
        status_name = None
        if status_json:
            try:
                import ast
                status_dict = ast.literal_eval(status_json)
                status_name = status_dict.get('name', '')
            except:
                pass
        
        # Find developer IDs
        assignee_email, _, _ = extract_developer_from_jira_json(assignee_json)
        creator_email, _, _ = extract_developer_from_jira_json(creator_json)
        
        assignee_id = find_developer_id_by_email(new_conn, assignee_email) if assignee_email else None
        creator_id = find_developer_id_by_email(new_conn, creator_email) if creator_email else None
        
        # Parse dates to local
        created_dt = parse_jira_date_to_local(created, tz) if created else None
        updated_dt = parse_jira_date_to_local(updated, tz) if updated else None
        status_changed_dt = parse_jira_date_to_local(status_changed, tz) if status_changed else None
        
        created_date_local = created_dt.date().isoformat() if created_dt else None
        updated_date_local = updated_dt.date().isoformat() if updated_dt else None
        status_changed_date_local = status_changed_dt.date().isoformat() if status_changed_dt else None
        
        # Insert issue
        new_cursor.execute("""
            INSERT INTO issues (
                id, summary, status_name, assignee_id, creator_id,
                created_at, updated_at, created_date_local, updated_date_local,
                status_changed_at, status_changed_date_local
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            issue_id, summary, status_name, assignee_id, creator_id,
            created, updated, created_date_local, updated_date_local,
            status_changed, status_changed_date_local
        ))
        
        count += 1
    
    new_conn.commit()
    console.print(f"[bold green]✓ Normalized {count} issues[/bold green]")
    
    return count


def link_issues_to_sprints(old_conn, new_conn):
    """Extract issue-sprint relationships from customfield_10020.
    
    Args:
        old_conn: Connection to old database
        new_conn: Connection to new database
    
    Returns:
        Count of relationships created
    """
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()
    
    # Check if customfield_10020 exists
    old_cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in old_cursor.fetchall()]
    
    if 'customfield_10020' not in columns:
        console.print("[bold yellow]No customfield_10020 (sprint field) found[/bold yellow]")
        return 0
    
    old_cursor.execute(f"SELECT id, customfield_10020 FROM {TABLE_NAME} WHERE customfield_10020 IS NOT NULL AND customfield_10020 != ''")
    
    count = 0
    
    for row in old_cursor.fetchall():
        issue_id, sprint_json = row
        
        try:
            import ast
            import json
            
            # Try JSON first, then ast.literal_eval
            try:
                sprint_list = json.loads(sprint_json)
            except json.JSONDecodeError:
                sprint_list = ast.literal_eval(sprint_json)
            
            # Handle both single sprint and list of sprints
            if isinstance(sprint_list, list):
                for sprint in sprint_list:
                    if isinstance(sprint, dict) and 'id' in sprint:
                        new_cursor.execute("""
                            INSERT OR IGNORE INTO issue_sprints (issue_id, sprint_id)
                            VALUES (?, ?)
                        """, (issue_id, sprint['id']))
                        count += 1
            elif isinstance(sprint_list, dict) and 'id' in sprint_list:
                new_cursor.execute("""
                    INSERT OR IGNORE INTO issue_sprints (issue_id, sprint_id)
                    VALUES (?, ?)
                """, (issue_id, sprint_list['id']))
                count += 1
        
        except Exception:
            pass  # Skip malformed sprint data
    
    new_conn.commit()
    console.print(f"[bold green]✓ Linked {count} issue-sprint relationships[/bold green]")
    
    return count


# (Continued in next message due to length...)

# ============================================================================
# EVENT EXTRACTION - JIRA
# ============================================================================

def extract_jira_events(old_conn, new_conn, sprint_date_map):
    """Extract Jira activity events from issues table.
    
    Creates events for:
        - Issue created
        - Issue updated
        - Status changed
    
    Args:
        old_conn: Connection to old database
        new_conn: Connection to new normalized database
        sprint_date_map: List of sprint date ranges
    
    Returns:
        Count of events created
    """
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()
    
    # Get all issues with timestamps
    old_cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in old_cursor.fetchall()]
    
    fields = ['id', 'creator', 'created', 'assignee', 'updated']
    if 'statuscategorychangedate' in columns:
        fields.append('statuscategorychangedate')
    
    query = f"SELECT {', '.join(fields)} FROM {TABLE_NAME}"
    old_cursor.execute(query)
    
    tz = get_local_timezone()
    count = 0
    
    for row in old_cursor.fetchall():
        issue_id = row[0]
        creator_json = row[1] if len(row) > 1 else None
        created = row[2] if len(row) > 2 else None
        assignee_json = row[3] if len(row) > 3 else None
        updated = row[4] if len(row) > 4 else None
        status_changed = row[5] if len(row) > 5 and 'statuscategorychangedate' in columns else None
        
        # EVENT 1: Issue Created
        if created and creator_json:
            creator_email, _, _ = extract_developer_from_jira_json(creator_json)
            creator_id = find_developer_id_by_email(new_conn, creator_email)
            
            if creator_id:
                created_dt = parse_jira_date_to_local(created, tz)
                if created_dt:
                    event_date = created_dt.date()
                    event_hour = created_dt.hour
                    time_bucket = get_time_bucket(created_dt)
                    sprint_id = find_sprint_for_date(event_date, sprint_date_map)
                    
                    new_cursor.execute("""
                        INSERT INTO jira_events (
                            developer_id, event_type, event_timestamp, event_date,
                            event_hour, time_bucket, issue_id, sprint_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        creator_id, 'created', created, event_date.isoformat(),
                        event_hour, time_bucket, issue_id, sprint_id
                    ))
                    count += 1
        
        # EVENT 2: Issue Updated
        if updated and assignee_json:
            assignee_email, _, _ = extract_developer_from_jira_json(assignee_json)
            assignee_id = find_developer_id_by_email(new_conn, assignee_email)
            
            if assignee_id:
                updated_dt = parse_jira_date_to_local(updated, tz)
                if updated_dt:
                    event_date = updated_dt.date()
                    event_hour = updated_dt.hour
                    time_bucket = get_time_bucket(updated_dt)
                    sprint_id = find_sprint_for_date(event_date, sprint_date_map)
                    
                    new_cursor.execute("""
                        INSERT INTO jira_events (
                            developer_id, event_type, event_timestamp, event_date,
                            event_hour, time_bucket, issue_id, sprint_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        assignee_id, 'updated', updated, event_date.isoformat(),
                        event_hour, time_bucket, issue_id, sprint_id
                    ))
                    count += 1
        
        # EVENT 3: Status Changed
        if status_changed and assignee_json:
            assignee_email, _, _ = extract_developer_from_jira_json(assignee_json)
            assignee_id = find_developer_id_by_email(new_conn, assignee_email)
            
            if assignee_id:
                status_changed_dt = parse_jira_date_to_local(status_changed, tz)
                if status_changed_dt:
                    event_date = status_changed_dt.date()
                    event_hour = status_changed_dt.hour
                    time_bucket = get_time_bucket(status_changed_dt)
                    sprint_id = find_sprint_for_date(event_date, sprint_date_map)
                    
                    new_cursor.execute("""
                        INSERT INTO jira_events (
                            developer_id, event_type, event_timestamp, event_date,
                            event_hour, time_bucket, issue_id, sprint_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        assignee_id, 'status_changed', status_changed, event_date.isoformat(),
                        event_hour, time_bucket, issue_id, sprint_id
                    ))
                    count += 1
    
    new_conn.commit()
    console.print(f"[bold green]✓ Extracted {count} Jira events[/bold green]")
    
    return count


# ============================================================================
# EVENT EXTRACTION - GIT
# ============================================================================

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


# ============================================================================
# MATERIALIZATION
# ============================================================================

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


# ============================================================================
# MAIN NORMALIZATION ORCHESTRATION
# ============================================================================

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
        from .schema import get_table_stats
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
