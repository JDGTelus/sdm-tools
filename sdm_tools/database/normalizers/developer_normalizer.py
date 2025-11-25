"""Developer extraction and population for normalized database."""

from collections import defaultdict
from rich.console import Console
from ...config import TABLE_NAME, INCLUDED_EMAILS
from .email_normalizer import normalize_email, extract_developer_from_jira_json

console = Console()


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
