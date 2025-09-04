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
import subprocess


console = Console()


JIRA_URL = os.getenv('JIRA_URL')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
JIRA_EMAIL = os.getenv('JIRA_EMAIL')
JQL_QUERY = os.getenv('JQL_QUERY', 'project = "SET" AND component = "IOTMI 3P Connector"')
DISPLAY_COLUMNS = os.getenv('DISPLAY_COLUMNS', 'key,summary,assignee,status').split(',')
DB_NAME = os.getenv('DB_NAME', 'sdm_tools.db')
TABLE_NAME = os.getenv('TABLE_NAME', 'iotmi_3p_issues')
REPO_PATH = os.getenv('REPO_PATH')


def print_banner():
    """ Prints the ASCII art banner. """
    f = Figlet(font='slant')
    ascii_art = f.renderText('SDM-Tools')
    console.print(f"[bold green]{ascii_art}[/bold green]")
    console.print("[bold blue]Customized insights and actions for SDMs.[/bold blue]")


def clear_screen():
    """ Clears the terminal screen. """
    subprocess.run('clear', shell=True)


def fetch_issue_ids():
    """ Fetches issue IDs from Jira using JQL. """
    url = f"{JIRA_URL}/rest/api/3/search/jql"
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    params = {'jql': JQL_QUERY, 'maxResults': 50}

    response = requests.post(
        url,
        headers=headers,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
        json=params
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
        'fields': ['*all']  # Fetch all fields
    }

    response = requests.post(
        url,
        headers=headers,
        auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
        json=data
    )

    if response.status_code != 200:
        raise Exception(f"Failed to fetch issue details: {response.status_code} - {response.text}")

    return response.json().get('issues', [])


def backup_table(conn, table_name):
    """ Backs up the current table by renaming it with a timestamp. """
    cursor = conn.cursor()
    backup_table_name = f"{table_name}_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    cursor.execute(f"ALTER TABLE {table_name} RENAME TO {backup_table_name}")
    console.print(f"[bold yellow]Table backed up to {backup_table_name}[/bold yellow]")


def create_table_from_issues(conn, issues):
    """ Creates a table with all fields from the Jira API response. """
    cursor = conn.cursor()

    # Collect all possible fields from all issues
    all_fields = set()
    for issue in issues:
        all_fields.update({k for k, v in issue['fields'].items() if v is not None})

    # Create table schema dynamically
    columns = ', '.join(f'{field} TEXT' for field in all_fields)
    cursor.execute(f"CREATE TABLE IF NOT EXISTS {TABLE_NAME} (id TEXT PRIMARY KEY, {columns})")


def store_issues_in_db(issues):
    """ Stores issues in the SQLite3 database. """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Check if the table exists
    cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
    if cursor.fetchone():
        backup_table(conn, TABLE_NAME)
        create_table_from_issues(conn, issues)
    else:
        create_table_from_issues(conn, issues)

    for issue in issues:
        fields = {k: v for k, v in issue['fields'].items() if v is not None}
        values = [issue['id']] + [str(fields.get(field, '')) for field in fields.keys()]
        cursor.execute(f'''
            INSERT OR REPLACE INTO {TABLE_NAME} (id, {', '.join(fields.keys())})
            VALUES (?, {', '.join(['?'] * len(fields.keys()))})
        ''', values)

    conn.commit()
    conn.close()


def display_issues():
    """ Displays issues in a table format. """
    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database does not exist. Please update issues from Jira first.[/bold red]")
        input("Press Enter to return to the menu...")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Fetch column names from the table
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns_in_db = [info[1] for info in cursor.fetchall()]

    # Check if DISPLAY_COLUMNS exist in the database
    if not all(column in columns_in_db for column in DISPLAY_COLUMNS):
        console.print("[bold red]Some DISPLAY_COLUMNS do not exist in the table. Defaulting to all columns.[/bold red]")
        columns_to_display = columns_in_db
    else:
        columns_to_display = DISPLAY_COLUMNS

    cursor.execute('SELECT ' + ', '.join(columns_to_display) + f' FROM {TABLE_NAME}')
    rows = cursor.fetchall()

    table = Table(show_header=True, header_style="bold magenta")
    for column in columns_to_display:
        table.add_column(column)

    for row in rows:
        table.add_row(*[str(item) for item in row])

    # Capture the table output and pipe it to less
    with console.capture() as capture:
        console.print(table)
    subprocess.run(['less'], input=capture.get().encode('utf-8'))

    conn.close()


def fetch_earliest_ticket_date():
    """ Fetches the creation date of the earliest Jira ticket from the database. """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(f"SELECT MIN(created) FROM {TABLE_NAME}")
    earliest_date = cursor.fetchone()[0]

    conn.close()

    # Convert date to YYYY-MM-DD format
    if earliest_date:
        parsed_date = datetime.strptime(earliest_date, "%Y-%m-%dT%H:%M:%S.%f%z")
        formatted_date = parsed_date.strftime("%Y-%m-%d")
        return formatted_date
    return None


def fetch_git_commits_since(date):
    """ Fetches commit information from the Git repository starting from the given date. """
    if not REPO_PATH or not os.path.exists(REPO_PATH):
        console.print("[bold red]Repository path is not set or does not exist. Please check the REPO_PATH environment variable.[/bold red]")
        input("Press Enter to return to the menu...")
        return []

    # Save the current working directory
    original_cwd = os.getcwd()
    os.chdir(REPO_PATH)
    try:
        commits = subprocess.check_output(['git', 'log', f'--since={date}', '--pretty=format:%H|%an|%ae|%ad|%s']).decode('utf-8').split('\n')
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to fetch commits: {e}[/bold red]")
        commits = []
    finally:
        # Return to the original working directory
        os.chdir(original_cwd)

    return commits


def create_git_commits_table(conn):
    """ Creates the git_commits table if it does not exist. """
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS git_commits (
            hash TEXT PRIMARY KEY,
            author_name TEXT,
            author_email TEXT,
            date TEXT,
            message TEXT
        )
    ''')


def store_commits_in_db(commits):
    """ Stores commit information in the SQLite3 database. """
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Backup the table if it exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'")
    if cursor.fetchone():
        backup_table(conn, 'git_commits')

    # Create the table if it doesn't exist
    create_git_commits_table(conn)

    # Store commits
    for commit in commits:
        if commit.strip():
            try:
                hash, author_name, author_email, date, message = commit.split('|', 4)
                cursor.execute('''
                    INSERT OR REPLACE INTO git_commits (hash, author_name, author_email, date, message)
                    VALUES (?, ?, ?, ?, ?)
                ''', (hash, author_name, author_email, date, message))
            except ValueError:
                console.print(f"[bold red]Error processing commit: {commit}[/bold red]")

    conn.commit()
    conn.close()


def update_git_commits():
    """ Updates the git_commits table with commits since the earliest Jira ticket date. """
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

    # Store commits in database
    store_commits_in_db(commits)

    console.print("[bold green]Commits since the earliest Jira ticket date have been stored in the database.[/bold green]")
    display_commits()


def display_commits():
    """ Displays commit information from the git_commits table. """
    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database does not exist. Please update commits first.[/bold red]")
        input("Press Enter to return to the menu...")
        return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Check if the table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'")
    if not cursor.fetchone():
        console.print("[bold red]No commit data found in the database. Please update commits first.[/bold red]")
        input("Press Enter to return to the menu...")
        return

    cursor.execute("SELECT * FROM git_commits")
    rows = cursor.fetchall()

    table = Table(show_header=True, header_style="bold magenta")
    headers = ["Hash", "Author Name", "Author Email", "Date", "Message"]
    for header in headers:
        table.add_column(header)

    for row in rows:
        table.add_row(*[str(item) for item in row])

    # Capture the table output and pipe it to less
    with console.capture() as capture:
        console.print(table)
    subprocess.run(['less'], input=capture.get().encode('utf-8'))

    conn.close()


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """SDM Tools: Manage your team's Jira tasks with style!"""
    manage_issues()


@cli.command()
def manage_issues():
    """Manage Jira issues."""
    while True:
        clear_screen()
        print_banner()
        console.print("[bold yellow]Choose an option:[/bold yellow]")
        console.print("[bold cyan]1. Update and display issues from Jira[/bold cyan]")
        console.print("[bold cyan]2. Display issues from stored data[/bold cyan]")
        console.print("[bold cyan]3. Update commit information from repository[/bold cyan]")
        console.print("[bold cyan]4. Display commit information from stored data[/bold cyan]")
        console.print("[bold cyan]5. Exit[/bold cyan]")

        choice = console.input("[bold magenta]Enter your choice (1/2/3/4/5): [/bold magenta]")

        if choice == '1':
            issue_ids = fetch_issue_ids()
            issues = fetch_issue_details(issue_ids)
            if issues:
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
                if cursor.fetchone():
                    backup_table(conn, TABLE_NAME)
                conn.close()
                store_issues_in_db(issues)
                console.print("[bold green]Issues updated from Jira and stored in the database.[/bold green]")
                display_issues()
        elif choice == '2':
            if os.path.exists(DB_NAME):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
                if cursor.fetchone():
                    display_issues()
                else:
                    console.print("[bold red]No issues data found in the database. Please run option 1 to update issues from Jira first.[/bold red]")
                    input("Press Enter to return to the menu...")
            else:
                console.print("[bold red]Database does not exist. Please run option 1 to update issues from Jira first.[/bold red]")
                input("Press Enter to return to the menu...")
        elif choice == '3':
            if os.path.exists(DB_NAME):
                conn = sqlite3.connect(DB_NAME)
                cursor = conn.cursor()
                cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
                if cursor.fetchone():
                    update_git_commits()
                else:
                    console.print("[bold red]No Jira issues found in the database. Please run option 1 to update issues from Jira first.[/bold red]")
                    input("Press Enter to return to the menu...")
            else:
                console.print("[bold red]Database does not exist. Please run option 1 to update issues from Jira first.[/bold red]")
                input("Press Enter to return to the menu...")
        elif choice == '4':
            display_commits()
        elif choice == '5':
            console.print("[bold red]Exiting SDM Tools.[/bold red]")
            break
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
            input("Press Enter to return to the menu...")


if __name__ == "__main__":
    cli()
