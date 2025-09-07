"""Git and CodeCommit repo handler"""
import subprocess
import os
import json
from datetime import datetime, timezone
from rich.console import Console
from .config import REPO_PATH, REPO_NAME


console = Console()


def fetch_git_commits_since(date):
    """ Fetches commit information from the Git repository starting from the given date. """
    if not REPO_PATH or not os.path.exists(REPO_PATH):
        console.print(
            "[bold red]Repository path is not set or does not exist. Please check the REPO_PATH environment variable.[/bold red]")
        input("Press Enter to return to the menu...")
        return []

    original_cwd = os.getcwd()
    os.chdir(REPO_PATH)
    try:
        commits = subprocess.check_output(
            ['git', 'log', f'--since={date}', '--pretty=format:%H|%an|%ae|%ad|%s']).decode('utf-8').split('\n')
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to fetch commits: {e}[/bold red]")
        commits = []
    finally:
        os.chdir(original_cwd)

    return commits


def fetch_git_merges_since(date):
    """ Fetches merge information from the Git repository. """
    if not REPO_PATH or not os.path.exists(REPO_PATH):
        console.print(
            "[bold red]Repository path is not set or does not exist. Please check the REPO_PATH environment variable.[/bold red]")
        input("Press Enter to return to the menu...")
        return []

    original_cwd = os.getcwd()
    os.chdir(REPO_PATH)
    try:
        merges = subprocess.check_output(
            ['git', 'log', '--merges', f'--since={date}', '--pretty=format:%H|%an|%ae|%ad|%s']).decode('utf-8').split('\n')
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to fetch merges: {e}[/bold red]")
        merges = []
    finally:
        os.chdir(original_cwd)

    return merges


def run_aws_cli_command(command, timeout=30):
    """Runs an AWS CLI command and returns the output."""
    console.print(f"[bold blue]Running AWS CLI command: {command}[/bold blue]")
    try:
        result = subprocess.check_output(command, shell=True, timeout=timeout).decode('utf-8')
        console.print(f"[bold green]Command output: {result}[/bold green]")
        return result
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to run AWS CLI command: {e}[/bold red]")
        return None
    except subprocess.TimeoutExpired as e:
        console.print(f"[bold red]AWS CLI command timed out: {e}[/bold red]")
        return None


def get_codecommit_commit(commit_id):
    """Gets information about a specific commit."""
    command = f"aws codecommit get-commit --repository-name {REPO_NAME} --commit-id {commit_id}"
    return run_aws_cli_command(command)


def list_codecommit_pull_requests(since_date=None):
    """Lists all pull requests for a specific CodeCommit repository and filters them by date."""
    # Fetch the earliest ticket date from Jira if no date is supplied
    if since_date is None:
        earliest_date_str = fetch_earliest_ticket_date()
        since_date = datetime.strptime(earliest_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)

    command = f"aws codecommit list-pull-requests --repository-name {REPO_NAME} --output json"
    result = run_aws_cli_command(command)
    if result:
        try:
            # Parse the JSON output
            pull_requests = json.loads(result).get('pullRequestIds', [])
            # Sort pull requests in descending order (assuming largest ID is latest)
            pull_requests.sort(reverse=True)

            filtered_pull_requests = []

            for pull_request_id in pull_requests:
                pull_request_details = get_codecommit_pull_request(pull_request_id)
                if pull_request_details:
                    creation_date = pull_request_details['pullRequest']['creationDate']
                    # Convert creation date to datetime object
                    creation_date_obj = datetime.strptime(creation_date, "%Y-%m-%dT%H:%M:%S.%f%z")
                    # Filter by the since_date
                    if creation_date_obj >= since_date:
                        filtered_pull_requests.append(pull_request_id)
                    else:
                        # Stop once we reach a pull request older than since_date
                        break

            console.print(f"[bold green]Found {len(filtered_pull_requests)} pull requests since {since_date}.[/bold green]")
            return filtered_pull_requests
        except json.JSONDecodeError:
            console.print("[bold red]Failed to parse pull request data.[/bold red]")
            return []
    return []


def get_codecommit_pull_request(pull_request_id):
    """Gets information about a specific pull request."""
    command = f"aws codecommit get-pull-request --pull-request-id {pull_request_id} --output json"
    result = run_aws_cli_command(command)
    if result:
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            console.print("[bold red]Failed to parse pull request details.[/bold red]")
            return None
    return None


def list_codecommit_branches():
    """Lists all branches in a specific CodeCommit repository."""
    command = f"aws codecommit list-branches --repository-name {REPO_NAME}"
    return run_aws_cli_command(command)
