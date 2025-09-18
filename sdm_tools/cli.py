"""CLI handler"""
import click
from datetime import datetime, timezone
from .utils import clear_screen, print_banner, console
from .jira import fetch_issue_ids, fetch_issue_details
from .database import (
    store_issues_in_db, display_issues, update_git_commits, display_commits
)
from .analytics import run_analytics_report


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
        console.print(
            "[bold cyan]1. Update and display issues from Jira[/bold cyan]")
        console.print(
            "[bold cyan]2. Display issues from stored data[/bold cyan]")
        console.print(
            "[bold cyan]3. Update commit information from repository[/bold cyan]")
        console.print(
            "[bold cyan]4. Display commit information from stored data[/bold cyan]")
        console.print(
            "[bold magenta]5. Update Developer Performance Analytics[/bold magenta]")
        console.print(
            "[bold magenta]6. Display Developer Performance Analytics[/bold magenta]")
        console.print("[bold cyan]7. Exit[/bold cyan]")
        choice = console.input(
            "[bold green]Enter your choice (1/2/3/4/5/6/7): [/bold green]")
        if choice == '1':
            issue_ids = fetch_issue_ids()
            issues = fetch_issue_details(issue_ids)
            if issues:
                store_issues_in_db(issues)
                console.print(
                    "[bold green]Issues updated from Jira and stored in the database.[/bold green]")
                display_issues()
        elif choice == '2':
            display_issues()
        elif choice == '3':
            update_git_commits()
            console.print(
                "[bold green]Commits since the earliest Jira ticket date have been stored in the database.[/bold green]")
            display_commits()
        elif choice == '4':
            display_commits()
        elif choice == '5':
            console.print(
                "[bold blue]🔍 Updating Developer Performance Analytics...[/bold blue]")
            try:
                from .analytics import update_analytics_data
                update_analytics_data()
                console.print(
                    "[bold green]Analytics data updated successfully![/bold green]")
            except Exception as e:
                console.print(
                    f"[bold red]Error updating analytics: {e}[/bold red]")
            input("Press Enter to return to the menu...")
        elif choice == '6':
            console.print(
                "[bold blue]📊 Displaying Developer Performance Analytics...[/bold blue]")
            try:
                from .analytics import display_analytics_reports
                display_analytics_reports()
            except Exception as e:
                console.print(
                    f"[bold red]Error displaying analytics: {e}[/bold red]")
            input("Press Enter to return to the menu...")
        elif choice == '7':
            console.print("[bold red]Exiting SDM Tools.[/bold red]")
            break
        else:
            console.print(
                "[bold red]Invalid choice. Please try again.[/bold red]")
            input("Press Enter to return to the menu...")


if __name__ == "__main__":
    cli()
