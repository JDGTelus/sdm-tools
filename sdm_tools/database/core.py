"""Core database functionality."""
import sqlite3
from datetime import datetime
from rich.console import Console

console = Console()


def execute_sql(conn, query, params=()):
    """Executes a SQL query and returns the result."""
    cursor = conn.cursor()
    cursor.execute(query, params)
    return cursor


def backup_table(conn, table_name):
    """Backs up the current table by renaming it with a timestamp."""
    backup_table_name = f"{table_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    execute_sql(
        conn, f"ALTER TABLE {table_name} RENAME TO {backup_table_name}")
    console.print(
        f"[bold yellow]Table backed up to {backup_table_name}[/bold yellow]")


def create_table(conn, table_name, columns):
    """Creates a table with specified columns."""
    # Remove 'id' from columns if it exists, as it's added separately as a primary key
    columns = [col for col in columns if col != 'id']
    columns_definition = ', '.join(f'{col} TEXT' for col in columns)
    execute_sql(
        conn, f"CREATE TABLE IF NOT EXISTS {table_name} (id TEXT PRIMARY KEY, {columns_definition})")
