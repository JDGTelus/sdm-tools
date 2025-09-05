"""DB handler"""
import sqlite3
import os
from datetime import datetime
from rich.console import Console
from rich.table import Table
import subprocess
from .config import DB_NAME, TABLE_NAME, DISPLAY_COLUMNS
from .git import fetch_git_commits_since


console = Console()


def execute_sql(conn, query, params=()):
    """ Executes a SQL query and returns the result. """
    cursor = conn.cursor()
    cursor.execute(query, params)
    return cursor


def backup_table(conn, table_name):
    """ Backs up the current table by renaming it with a timestamp. """
    backup_table_name = f"{table_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    execute_sql(conn, f"ALTER TABLE {table_name} RENAME TO {backup_table_name}")
    console.print(f"[bold yellow]Table backed up to {backup_table_name}[/bold yellow]")


def create_table(conn, table_name, columns):
    """ Creates a table with specified columns. """
    columns_definition = ', '.join(f'{col} TEXT' for col in columns)
    execute_sql(conn, f"CREATE TABLE IF NOT EXISTS {table_name} (id TEXT PRIMARY KEY, {columns_definition})")


def store_issues_in_db(issues):
    """ Stores issues in the SQLite3 database. """
    with sqlite3.connect(DB_NAME) as conn:
        if execute_sql(conn, f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'").fetchone():
            backup_table(conn, TABLE_NAME)
        all_fields = {k for issue in issues for k, v in issue['fields'].items() if v is not None}
        create_table(conn, TABLE_NAME, all_fields)

        for issue in issues:
            fields = {k: v for k, v in issue['fields'].items() if v is not None}
            values = [issue['id']] + [str(fields.get(field, '')) for field in fields.keys()]
            execute_sql(conn, f'''
                INSERT OR REPLACE INTO {TABLE_NAME} (id, {', '.join(fields.keys())})
                VALUES (?, {', '.join(['?'] * len(fields.keys()))})
            ''', values)


def display_table_data(conn, table_name, columns):
    """ Displays data from a specified table in a formatted table. """
    cursor = execute_sql(conn, f"SELECT {', '.join(columns)} FROM {table_name}")
    rows = cursor.fetchall()

    table = Table(show_header=True, header_style="bold magenta")
    for column in columns:
        table.add_column(column)

    for row in rows:
        table.add_row(*[str(item) for item in row])

    with console.capture() as capture:
        console.print(table)
    subprocess.run(['less'], input=capture.get().encode('utf-8'))


def display_issues():
    """ Displays issues in a table format. """
    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database does not exist. Please update issues from Jira first.[/bold red]")
        input("Press Enter to return to the menu...")
        return

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Check if the table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
        if not cursor.fetchone():
            console.print("[bold red]No issues data found in the database. Please run option 1 to update issues from Jira first.[/bold red]")
            input("Press Enter to return to the menu...")
            return

        # Fetch column names from the table
        cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
        columns_in_db = [info[1] for info in cursor.fetchall()]

        # Check if DISPLAY_COLUMNS exist in the database
        if not all(column in columns_in_db for column in DISPLAY_COLUMNS):
            console.print("[bold red]Some DISPLAY_COLUMNS do not exist in the table. Defaulting to all columns.[/bold red]")
            columns_to_display = columns_in_db
        else:
            columns_to_display = DISPLAY_COLUMNS

        display_table_data(conn, TABLE_NAME, columns_to_display)


def fetch_earliest_ticket_date():
    """ Fetches the creation date of the earliest Jira ticket from the database. """
    with sqlite3.connect(DB_NAME) as conn:
        earliest_date = execute_sql(conn, f"SELECT MIN(created) FROM {TABLE_NAME}").fetchone()[0]

    if earliest_date:
        parsed_date = datetime.strptime(earliest_date, "%Y-%m-%dT%H:%M:%S.%f%z")
        return parsed_date.strftime("%Y-%m-%d")
    return None


def update_git_commits():
    """ Updates the git_commits table with commits since the earliest Jira ticket date. """
    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database does not exist. Please run option 1 to update issues from Jira first.[/bold red]")
        input("Press Enter to return to the menu...")
        return

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Check if the issues table exists
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
        if not cursor.fetchone():
            console.print("[bold red]No Jira issues found in the database. Please run option 1 to update issues from Jira first.[/bold red]")
            input("Press Enter to return to the menu...")
            return

        # Fetch the earliest ticket date
        earliest_date = fetch_earliest_ticket_date()

    if not earliest_date:
        console.print("[bold red]No Jira issues found in the database.[/bold red]")
        input("Press Enter to return to the menu...")
        return

    console.print(f"[bold green]Earliest Jira ticket creation date: {earliest_date}[/bold green]")

    commits = fetch_git_commits_since(earliest_date)
    if not commits:
        console.print("[bold red]No commits found since the earliest Jira ticket date.[/bold red]")
        input("Press Enter to return to the menu...")
        return

    store_commits_in_db(commits)
    console.print("[bold green]Commits since the earliest Jira ticket date have been stored in the database.[/bold green]")
    display_commits()


def store_commits_in_db(commits):
    """ Stores commit information in the SQLite3 database. """
    with sqlite3.connect(DB_NAME) as conn:
        if execute_sql(conn, "SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'").fetchone():
            backup_table(conn, 'git_commits')
        create_git_commits_table(conn)

        for commit in commits:
            if commit.strip():
                try:
                    hash, author_name, author_email, date, message = commit.split('|', 4)
                    execute_sql(conn, '''
                        INSERT OR REPLACE INTO git_commits (hash, author_name, author_email, date, message)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (hash, author_name, author_email, date, message))
                except ValueError:
                    console.print(f"[bold red]Error processing commit: {commit}[/bold red]")


def create_git_commits_table(conn):
    """ Creates the git_commits table if it does not exist. """
    execute_sql(conn, '''
        CREATE TABLE IF NOT EXISTS git_commits (
            hash TEXT PRIMARY KEY,
            author_name TEXT,
            author_email TEXT,
            date TEXT,
            message TEXT
        )
    ''')


def display_commits():
    """ Displays commit information from the git_commits table. """
    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database does not exist. Please update commits first.[/bold red]")
        input("Press Enter to return to the menu...")
        return

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Check if the table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'")
        if not cursor.fetchone():
            console.print("[bold red]No commit data found in the database. Please update commits first.[/bold red]")
            input("Press Enter to return to the menu...")
            return

        # Fetch column names from the table
        cursor.execute("PRAGMA table_info(git_commits)")
        columns_in_db = [info[1] for info in cursor.fetchall()]

        columns_to_display = ["hash", "author_name", "author_email", "date", "message"]

        if not all(column in columns_in_db for column in columns_to_display):
            console.print("[bold red]Some columns do not exist in the table. Defaulting to all columns.[/bold red]")
            columns_to_display = columns_in_db

        display_table_data(conn, 'git_commits', columns_to_display)
