"""CLI handler"""
import click
from datetime import datetime, timezone
from .utils import clear_screen, print_banner, console
from .jira import fetch_issue_ids, fetch_issue_details
from .repo import (
    fetch_git_merges_since, list_codecommit_pull_requests
)
from .database import (
    store_issues_in_db, display_issues, update_git_commits, display_commits,
    store_codecommit_pull_requests_in_db, display_codecommit_pull_requests,
    store_codecommit_merges_in_db, display_codecommit_merges,
    store_codecommit_reviews_in_db, display_codecommit_reviews
)


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
        console.print("[bold cyan]5. Update and display CodeCommit pull requests[/bold cyan]")
        console.print("[bold cyan]6. Update and display CodeCommit merges[/bold cyan]")
        console.print("[bold cyan]7. Update and display CodeCommit reviews[/bold cyan]")
        console.print("[bold cyan]8. Exit[/bold cyan]")

        choice = console.input("[bold green]Enter your choice (1/2/3/4/5/6/7/8): [/bold green]")

        if choice == '1':
            issue_ids = fetch_issue_ids()
            issues = fetch_issue_details(issue_ids)
            if issues:
                store_issues_in_db(issues)
                console.print("[bold green]Issues updated from Jira and stored in the database.[/bold green]")
                display_issues()
        elif choice == '2':
            display_issues()
        elif choice == '3':
            update_git_commits()
            console.print("[bold green]Commits since the earliest Jira ticket date have been stored in the database.[/bold green]")
            display_commits()
        elif choice == '4':
            display_commits()
        elif choice == '5':
            since_date_str = console.input("[bold green]Enter the start date (YYYY-MM-DD) or leave blank for earliest commit date: [/bold green]")
            if since_date_str:
                since_date = datetime.strptime(since_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                since_date = None
            pull_requests = list_codecommit_pull_requests(since_date)
            if pull_requests:
                store_codecommit_pull_requests_in_db(pull_requests)
                console.print("[bold green]CodeCommit pull requests updated and stored in the database.[/bold green]")
                display_codecommit_pull_requests()
        elif choice == '6':
            since_date_str = console.input("[bold green]Enter the start date (YYYY-MM-DD) or leave blank for earliest commit date: [/bold green]")
            if since_date_str:
                since_date = datetime.strptime(since_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            else:
                since_date = None
            merges = fetch_git_merges_since(since_date)
            if merges:
                store_codecommit_merges_in_db(merges)
                console.print("[bold green]CodeCommit merges updated and stored in the database.[/bold green]")
                display_codecommit_merges()
        elif choice == '7':
            reviews = []  # Placeholder for actual review fetching logic
            if reviews:
                store_codecommit_reviews_in_db(reviews)
                console.print("[bold green]CodeCommit reviews updated and stored in the database.[/bold green]")
                display_codecommit_reviews()
        elif choice == '8':
            console.print("[bold red]Exiting SDM Tools.[/bold red]")
            break
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
            input("Press Enter to return to the menu...")


if __name__ == "__main__":
    cli()
