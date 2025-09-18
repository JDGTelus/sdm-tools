"""Issues database functionality."""
import os
import subprocess
import sqlite3
from rich.console import Console
from rich.table import Table
from .core import execute_sql, backup_table, create_table
from ..config import DB_NAME, TABLE_NAME, DISPLAY_COLUMNS

console = Console()


def store_issues_in_db(issues):
    """Stores issues in the SQLite3 database."""
    with sqlite3.connect(DB_NAME) as conn:
        if execute_sql(conn, f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'").fetchone():
            backup_table(conn, TABLE_NAME)
        all_fields = {k for issue in issues for k,
                      v in issue['fields'].items() if v is not None}
        create_table(conn, TABLE_NAME, all_fields)
        for issue in issues:
            fields = {k: v for k,
                      v in issue['fields'].items() if v is not None}
            values = [issue['id']] + \
                [str(fields.get(field, '')) for field in fields.keys()]
            execute_sql(conn, f'''
                INSERT OR REPLACE INTO {TABLE_NAME} (id, {', '.join(fields.keys())})
                VALUES (?, {', '.join(['?'] * len(fields.keys()))})
            ''', values)


def display_table_data(conn, table_name, columns):
    """Displays data from a specified table in a formatted table."""
    cursor = execute_sql(
        conn, f"SELECT {', '.join(columns)} FROM {table_name}")
    rows = cursor.fetchall()
    table = Table(show_header=True, header_style="bold green")
    for column in columns:
        table.add_column(column)
    for row in rows:
        table.add_row(*[str(item) for item in row])
    with console.capture() as capture:
        console.print(table)
    subprocess.run(['less'], input=capture.get().encode('utf-8'))


def display_issues():
    """Displays issues in a table format."""
    if not os.path.exists(DB_NAME):
        console.print(
            "[bold red]Database does not exist. Please update issues from Jira first.[/bold red]")
        input("Press Enter to return to the menu...")
        return
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Check if the table exists
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
        if not cursor.fetchone():
            console.print(
                "[bold red]No issues data found in the database. Please run option 1 to update issues from Jira first.[/bold red]")
            input("Press Enter to return to the menu...")
            return
        # Fetch column names from the table
        cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
        columns_in_db = [info[1] for info in cursor.fetchall()]
        # Check if DISPLAY_COLUMNS exist in the database
        if not all(column in columns_in_db for column in DISPLAY_COLUMNS):
            console.print(
                "[bold red]Some DISPLAY_COLUMNS do not exist in the table. Defaulting to all columns.[/bold red]")
            columns_to_display = columns_in_db
        else:
            columns_to_display = DISPLAY_COLUMNS
        display_table_data(conn, TABLE_NAME, columns_to_display)


def fetch_earliest_ticket_date():
    """Fetches the creation date of the earliest Jira ticket from the database."""
    with sqlite3.connect(DB_NAME) as conn:
        earliest_date = execute_sql(
            conn, f"SELECT MIN(created) FROM {TABLE_NAME}").fetchone()[0]
    if earliest_date:
        from datetime import datetime
        parsed_date = datetime.strptime(
            earliest_date, "%Y-%m-%dT%H:%M:%S.%f%z")
        return parsed_date.strftime("%Y-%m-%d")
    return None
