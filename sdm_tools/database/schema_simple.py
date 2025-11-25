"""Simplified 3-table database schema for SDM Tools."""

import sqlite3
from rich.console import Console

console = Console()


def create_simple_schema(conn):
    """Create simplified 3-table schema.
    
    Tables:
        1. developers: Developer registry with email normalization
        2. activity_events: Unified event log (Jira + Git)
        3. sprints: Sprint metadata
    
    Args:
        conn: SQLite connection object
    """
    cursor = conn.cursor()
    
    # ==========================================
    # 1. DEVELOPERS TABLE
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS developers (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            active BOOLEAN DEFAULT 1,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_developers_active ON developers(active)")
    
    # ==========================================
    # 2. ACTIVITY_EVENTS TABLE (Unified)
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            developer_email TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_timestamp TEXT NOT NULL,
            event_date DATE NOT NULL,
            
            -- Context (nullable)
            sprint_name TEXT,
            issue_key TEXT,
            commit_hash TEXT,
            
            -- Metadata (JSON blob for flexibility)
            metadata TEXT,
            
            FOREIGN KEY (developer_email) REFERENCES developers(email)
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_developer_date ON activity_events(developer_email, event_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_sprint ON activity_events(sprint_name, event_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_date ON activity_events(event_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_type ON activity_events(event_type)")
    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_events_commit_hash ON activity_events(commit_hash) WHERE commit_hash IS NOT NULL")
    
    # ==========================================
    # 3. SPRINTS TABLE
    # ==========================================
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sprints (
            name TEXT PRIMARY KEY,
            state TEXT,
            start_date DATE,
            end_date DATE,
            total_planned_points REAL DEFAULT 0,
            total_delivered_points REAL DEFAULT 0,
            jira_id INTEGER
        )
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sprints_dates ON sprints(start_date, end_date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sprints_state ON sprints(state)")
    
    conn.commit()
    console.print("[bold green]✓ Simplified 3-table schema created[/bold green]")


def drop_all_tables(conn):
    """Drop all tables from the database.
    
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
        if table_name != 'sqlite_sequence':  # Skip SQLite internal table
            cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
            console.print(f"[dim]Dropped table: {table_name}[/dim]")
    
    conn.commit()
    console.print(f"[bold yellow]Dropped {len(tables)} table(s)[/bold yellow]")


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
        if table_name == 'sqlite_sequence':
            continue
        
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        stats[table_name] = count
    
    return stats
