"""Git and CodeCommit repo handler"""
import subprocess
import os
from rich.console import Console
from .config import REPO_PATH


console = Console()


def run_aws_cli_command(command):
    """Runs an AWS CLI command and returns the output."""
    try:
        result = subprocess.check_output(command, shell=True).decode('utf-8')
        return result
    except subprocess.CalledProcessError as e:
        console.print(f"[bold red]Failed to run AWS CLI command: {e}[/bold red]")
        return None


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


def get_codecommit_commit(repo_name, commit_id):
    """Gets information about a specific commit."""
    command = f"aws codecommit get-commit --repository-name {repo_name} --commit-id {commit_id}"
    return run_aws_cli_command(command)


def list_codecommit_pull_requests(repo_name):
    """Lists all pull requests for a specific CodeCommit repository."""
    command = f"aws codecommit list-pull-requests --repository-name {repo_name}"
    return run_aws_cli_command(command)

def get_codecommit_pull_request(pull_request_id):
    """Gets information about a specific pull request."""
    command = f"aws codecommit get-pull-request --pull-request-id {pull_request_id}"
    return run_aws_cli_command(command)

def list_codecommit_branches(repo_name):
    """Lists all branches in a specific CodeCommit repository."""
    command = f"aws codecommit list-branches --repository-name {repo_name}"
    return run_aws_cli_command(command)

def get_codecommit_commit(repo_name, commit_id):
    """Gets information about a specific commit."""
    command = f"aws codecommit get-commit --repository-name {repo_name} --commit-id {commit_id}"
    return run_aws_cli_command(command)
