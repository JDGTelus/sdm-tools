""" SDM-Tools: Customized insights and actions for SDMs """
import os
import click
import requests
import sqlite3
from datetime import datetime
from requests.auth import HTTPBasicAuth
from rich.console import Console
from rich.table import Table
from pyfiglet import Figlet

console = Console()

JIRA_URL = os.getenv('JIRA_URL')
API_TOKEN = os.getenv('JIRA_API_TOKEN')
USER_EMAIL = os.getenv('JIRA_EMAIL')
ISSUE_TYPES = os.getenv('ISSUE_TYPES', 'Story,Bug').split(',')
DISPLAY_COLUMNS = os.getenv('DISPLAY_COLUMNS', 'key,summary,status').split(',')

DB_FILE = 'sdm_tools_jira_issues.db'


def print_banner():
    """ Prints the ASCII art banner. """
    f = Figlet(font='slant')
    ascii_art = f.renderText('SDM-Tools')
    console.print(f"[bold green]{ascii_art}[/bold green]")
    console.print("[bold blue]Customized insights and actions for SDMs.[/bold blue]")


def fetch_issue_ids():
    """ Fetches issue IDs from Jira using JQL. """
    url = f"{JIRA_URL}/rest/api/3/search/jql"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    jql_query = f'assignee="{USER_EMAIL}" AND issuetype IN ({",".join(ISSUE_TYPES)})'
    data = {'jql': jql_query, 'maxResults': 50}

    response = requests.post(
        url,
        headers=headers,
        auth=HTTPBasicAuth(USER_EMAIL, API_TOKEN),
        json=data
    )

    if response.status_code != 200:
        raise Exception(f"Failed to fetch issue IDs: {response.status_code} - {response.text}")

    return [issue['id'] for issue in response.json().get('issues', [])]


def fetch_issue_details(issue_ids):
    """ Fetches detailed issue data for given issue IDs. """
    url = f"{JIRA_URL}/rest/api/3/issue/bulkfetch"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    data = {
        'issueIdsOrKeys': issue_ids,
        'fields': ['key', 'summary', 'status', 'assignee', 'created', 'updated']
    }

    response = requests.post(
        url,
        headers=headers,
        auth=HTTPBasicAuth(USER_EMAIL, API_TOKEN),
        json=data
    )

    if response.status_code != 200:
        raise Exception(f"Failed to fetch issue details: {response.status_code} - {response.text}")

    return response.json().get('issues', [])


def backup_database():
    """ Backs up the current database. """
    backup_file = f'sdm_tools_jira_issues_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    if os.path.exists(DB_FILE):
        os.rename(DB_FILE, backup_file)
        console.print(f"[bold yellow]Database backed up to {backup_file}[/bold yellow]")


def store_issues_in_db(issues):
    """ Stores issues in the SQLite3 database. """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS JiraIssues (
            id TEXT PRIMARY KEY,
            key TEXT,
            summary TEXT,
            status TEXT,
            assignee TEXT,
            created TEXT,
            updated TEXT,
            raw_data TEXT
        )
    ''')

    for issue in issues:
        fields = issue['fields']
        raw_data = str(issue)
        cursor.execute('''
            INSERT OR REPLACE INTO JiraIssues (id, key, summary, status, assignee, created, updated, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            issue['id'],
            issue['key'],
            fields['summary'],
            fields['status']['name'],
            fields['assignee']['displayName'] if fields['assignee'] else None,
            fields['created'],
            fields['updated'],
            raw_data
        ))

    conn.commit()
    conn.close()


def display_issues():
    """ Displays issues in a table format. """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    cursor.execute('SELECT ' + ', '.join(DISPLAY_COLUMNS) + ' FROM JiraIssues')
    rows = cursor.fetchall()

    table = Table(show_header=True, header_style="bold magenta")
    for column in DISPLAY_COLUMNS:
        table.add_column(column)

    for row in rows:
        table.add_row(*[str(item) for item in row])

    console.print(table)
    conn.close()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """SDM Tools: Manage your team's Jira tasks with style!"""
    print_banner()
    if ctx.invoked_subcommand is None:
        manage_issues()


@cli.command()
def manage_issues():
    """Manage Jira issues."""
    console.print("[bold yellow]Choose an option:[/bold yellow]")
    console.print("[bold cyan]1. Update and display issues from Jira[/bold cyan]")
    console.print("[bold cyan]2. Display issues from stored data[/bold cyan]")
    console.print("[bold cyan]3. Exit[/bold cyan]")

    choice = console.input("[bold magenta]Enter your choice (1/2/3): [/bold magenta]")

    if choice == '1':
        backup_database()
        issue_ids = fetch_issue_ids()
        issues = fetch_issue_details(issue_ids)
        store_issues_in_db(issues)
        console.print("[bold green]Issues updated from Jira and stored in the database.[/bold green]")
        display_issues()
    elif choice == '2':
        display_issues()
    elif choice == '3':
        console.print("[bold red]Exiting SDM Tools.[/bold red]")
    else:
        console.print("[bold red]Invalid choice. Please try again.[/bold red]")


if __name__ == "__main__":
    cli()
