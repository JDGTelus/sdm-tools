"""Git repo handler"""
import subprocess
import os
from rich.console import Console
from .config import REPO_PATH


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
