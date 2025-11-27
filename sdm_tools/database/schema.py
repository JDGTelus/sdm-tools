"""Database schema definitions for normalized tables."""

from rich.console import Console

console = Console()


def create_normalized_schema(conn):
    """Create all normalized tables for the fresh database.

    Tables:
        - developers: Central developer registry
        - developer_email_aliases: Email variations for matching
        - sprints: Sprint information
        - issues: Simplified issue tracking
        - issue_sprints: Many-to-many issue-sprint relationship
        - jira_events: Activity events from Jira
        - git_events: Activity events from Git
        - daily_activity_summary: Pre-aggregated daily activity

    Args:
        conn: SQLite connection object
    """
    cursor = conn.cursor()

    # ==========================================
    # 1. DEVELOPERS TABLE
    # ==========================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS developers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            jira_account_id TEXT,
            active BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_developers_email ON developers(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_developers_active ON developers(active)")

    # ==========================================
    # 2. DEVELOPER EMAIL ALIASES
    # ==========================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS developer_email_aliases (
            developer_id INTEGER NOT NULL,
            alias_email TEXT NOT NULL,
            source TEXT,
            PRIMARY KEY (developer_id, alias_email),
            FOREIGN KEY (developer_id) REFERENCES developers(id) ON DELETE CASCADE
        )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_aliases_email ON developer_email_aliases(alias_email)"
    )

    # ==========================================
    # 3. SPRINTS TABLE
    # ==========================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS sprints (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            state TEXT,
            start_date TEXT,
            end_date TEXT,
            start_date_local DATE,
            end_date_local DATE,
            board_id INTEGER,
            goal TEXT
        )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_sprints_dates ON sprints(start_date_local, end_date_local)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sprints_state ON sprints(state)")

    # ==========================================
    # 4. ISSUES TABLE (Simplified)
    # ==========================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS issues (
            id TEXT PRIMARY KEY,
            summary TEXT,
            status_name TEXT,
            story_points REAL,
            assignee_id INTEGER,
            creator_id INTEGER,
            created_at TEXT,
            updated_at TEXT,
            created_date_local DATE,
            updated_date_local DATE,
            status_changed_at TEXT,
            status_changed_date_local DATE,
            FOREIGN KEY (assignee_id) REFERENCES developers(id),
            FOREIGN KEY (creator_id) REFERENCES developers(id)
        )
    """
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_issues_assignee ON issues(assignee_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_issues_created ON issues(created_date_local)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_issues_updated ON issues(updated_date_local)")

    # ==========================================
    # 5. ISSUE-SPRINT RELATIONSHIP
    # ==========================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS issue_sprints (
            issue_id TEXT NOT NULL,
            sprint_id INTEGER NOT NULL,
            PRIMARY KEY (issue_id, sprint_id),
            FOREIGN KEY (issue_id) REFERENCES issues(id) ON DELETE CASCADE,
            FOREIGN KEY (sprint_id) REFERENCES sprints(id) ON DELETE CASCADE
        )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_issue_sprints_sprint ON issue_sprints(sprint_id)"
    )

    # ==========================================
    # 6. JIRA EVENTS TABLE
    # ==========================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS jira_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            developer_id INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            event_timestamp TEXT NOT NULL,
            event_date DATE NOT NULL,
            event_hour INTEGER NOT NULL,
            time_bucket TEXT NOT NULL,
            issue_id TEXT,
            sprint_id INTEGER,
            FOREIGN KEY (developer_id) REFERENCES developers(id),
            FOREIGN KEY (issue_id) REFERENCES issues(id),
            FOREIGN KEY (sprint_id) REFERENCES sprints(id)
        )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_jira_events_dev_date ON jira_events(developer_id, event_date)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_jira_events_sprint ON jira_events(sprint_id, event_date)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_jira_events_date ON jira_events(event_date)")

    # ==========================================
    # 7. GIT EVENTS TABLE
    # ==========================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS git_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            developer_id INTEGER NOT NULL,
            commit_hash TEXT NOT NULL UNIQUE,
            commit_timestamp TEXT NOT NULL,
            commit_date DATE NOT NULL,
            commit_hour INTEGER NOT NULL,
            time_bucket TEXT NOT NULL,
            sprint_id INTEGER,
            message TEXT,
            FOREIGN KEY (developer_id) REFERENCES developers(id),
            FOREIGN KEY (sprint_id) REFERENCES sprints(id)
        )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_git_events_dev_date ON git_events(developer_id, commit_date)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_git_events_sprint ON git_events(sprint_id, commit_date)"
    )
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_git_events_date ON git_events(commit_date)")

    # ==========================================
    # 8. DAILY ACTIVITY SUMMARY (Materialized)
    # ==========================================
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS daily_activity_summary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activity_date DATE NOT NULL,
            developer_id INTEGER NOT NULL,
            sprint_id INTEGER,
            time_bucket TEXT NOT NULL,
            jira_count INTEGER DEFAULT 0,
            git_count INTEGER DEFAULT 0,
            total_count INTEGER DEFAULT 0,
            UNIQUE(activity_date, developer_id, time_bucket),
            FOREIGN KEY (developer_id) REFERENCES developers(id),
            FOREIGN KEY (sprint_id) REFERENCES sprints(id)
        )
    """
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_summary_date ON daily_activity_summary(activity_date)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_summary_sprint ON daily_activity_summary(sprint_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_summary_dev_date ON daily_activity_summary(developer_id, activity_date)"
    )

    conn.commit()
    console.print("[bold green]✓ Normalized schema created successfully[/bold green]")


def drop_all_tables(conn):
    """Drop all tables from the database for a fresh start.

    Args:
        conn: SQLite connection object
    """
    cursor = conn.cursor()

    # Get all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()

    if not tables:
        console.print("[yellow]No tables to drop[/yellow]")
        return

    # Drop all tables
    for table in tables:
        table_name = table[0]
        if table_name != "sqlite_sequence":  # Skip SQLite internal table
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            console.print(f"[dim]Dropped table: {table_name}[/dim]")

    conn.commit()
    console.print(f"[bold yellow]Dropped {len(tables)} tables[/bold yellow]")


def get_table_stats(conn):
    """Get statistics about all tables in the database.

    Args:
        conn: SQLite connection object

    Returns:
        Dict with table names and row counts
    """
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()

    stats = {}
    for table in tables:
        table_name = table[0]
        if table_name == "sqlite_sequence":
            continue

        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        stats[table_name] = count

    return stats
