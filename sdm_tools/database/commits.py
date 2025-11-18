"""Commits database functionality."""

import os
import sqlite3
from rich.console import Console
from .core import execute_sql, backup_table
from .issues import display_table_data, fetch_earliest_ticket_date
from .. import config
from ..repo import fetch_git_commits_since

console = Console()


def update_git_commits():
    """Updates the git_commits table with commits since the earliest Jira ticket date."""
    if not os.path.exists(config.DB_NAME):
        console.print(
            "[bold red]Database does not exist. Please run option 1 to update issues from Jira first.[/bold red]"
        )
        input("Press Enter to return to the menu...")
        return
    with sqlite3.connect(config.DB_NAME) as conn:
        cursor = conn.cursor()
        # Check if the issues table exists
        from ..config import TABLE_NAME

        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'"
        )
        if not cursor.fetchone():
            console.print(
                "[bold red]No Jira issues found in the database. Please run option 1 to update issues from Jira first.[/bold red]"
            )
            input("Press Enter to return to the menu...")
            return
        # Fetch the earliest ticket date
        earliest_date = fetch_earliest_ticket_date()
    if not earliest_date:
        console.print("[bold red]No Jira issues found in the database.[/bold red]")
        input("Press Enter to return to the menu...")
        return
    console.print(
        f"[bold green]Earliest Jira ticket creation date: {earliest_date}[/bold green]"
    )
    commits = fetch_git_commits_since(earliest_date)
    if not commits:
        console.print(
            "[bold red]No commits found since the earliest Jira ticket date.[/bold red]"
        )
        input("Press Enter to return to the menu...")
        return
    store_commits_in_db(commits)


def store_commits_in_db(commits):
    """Stores commit information in the SQLite3 database."""
    with sqlite3.connect(config.DB_NAME) as conn:
        if execute_sql(
            conn,
            "SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'",
        ).fetchone():
            backup_table(conn, "git_commits")
        create_git_commits_table(conn)
        for commit in commits:
            if commit.strip():
                try:
                    hash, author_name, author_email, date, message = commit.split(
                        "|", 4
                    )
                    execute_sql(
                        conn,
                        """
                        INSERT OR REPLACE INTO git_commits (hash, author_name, author_email, date, message)
                        VALUES (?, ?, ?, ?, ?)
                    """,
                        (hash, author_name, author_email, date, message),
                    )
                except ValueError:
                    console.print(
                        f"[bold red]Error processing commit: {commit}[/bold red]"
                    )


def create_git_commits_table(conn):
    """Creates the git_commits table if it does not exist."""
    execute_sql(
        conn,
        """
        CREATE TABLE IF NOT EXISTS git_commits (
            hash TEXT PRIMARY KEY,
            author_name TEXT,
            author_email TEXT,
            date TEXT,
            message TEXT
        )
    """,
    )


def display_commits():
    """Displays commit information from the git_commits table."""
    if not os.path.exists(config.DB_NAME):
        console.print(
            "[bold red]Database does not exist. Please update commits first.[/bold red]"
        )
        input("Press Enter to return to the menu...")
        return

    with sqlite3.connect(config.DB_NAME) as conn:
        cursor = conn.cursor()
        # Check if the table exists
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'"
        )
        if not cursor.fetchone():
            console.print(
                "[bold red]No commit data found in the database. Please update commits first.[/bold red]"
            )
            input("Press Enter to return to the menu...")
            return

        # Fetch column names from the table
        cursor.execute("PRAGMA table_info(git_commits)")
        columns_in_db = [info[1] for info in cursor.fetchall()]
        columns_to_display = ["hash", "author_name", "author_email", "date", "message"]

        if not all(column in columns_in_db for column in columns_to_display):
            console.print(
                "[bold red]Some columns do not exist in the table. Defaulting to all columns.[/bold red]"
            )
            columns_to_display = columns_in_db

        display_table_data(conn, "git_commits", columns_to_display)
