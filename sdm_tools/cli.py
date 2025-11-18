"""CLI handler"""

import os
import sqlite3
import click
from .utils import clear_screen, print_banner, console
from .jira import fetch_issue_ids, fetch_issue_details
from .database import (
    store_issues_in_db,
    display_issues,
    update_git_commits,
    display_commits,
    generate_daily_report_json,
    display_daily_report_summary,
)
from .config import DB_NAME, TABLE_NAME


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """SDM Tools: Manage your team's Jira tasks with style!"""
    manage_issues()


def has_issues_data():
    """Check if issues data exists in the database."""
    if not os.path.exists(DB_NAME):
        return False

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'"
        )
        if not cursor.fetchone():
            return False

        # Check if table has any data
        cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME}")
        count = cursor.fetchone()[0]
        return count > 0


def has_commits_data():
    """Check if commits data exists in the database."""
    if not os.path.exists(DB_NAME):
        return False

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'"
        )
        if not cursor.fetchone():
            return False

        # Check if table has any data
        cursor.execute("SELECT COUNT(*) FROM git_commits")
        count = cursor.fetchone()[0]
        return count > 0


def handle_issues_option():
    """Handle the unified issues option (get/update/display)."""
    if has_issues_data():
        # Data exists, ask if user wants to update
        update_choice = (
            console.input(
                "[bold yellow]Issues data already exists. Do you want to update it? (y/N): [/bold yellow]"
            )
            .strip()
            .lower()
        )

        if update_choice == "y" or update_choice == "yes":
            # User wants to update
            try:
                issue_ids = fetch_issue_ids()
                issues = fetch_issue_details(issue_ids)
                if issues:
                    store_issues_in_db(issues)
                    console.print(
                        "[bold green]Issues updated from Jira and stored in the database.[/bold green]"
                    )
                else:
                    console.print(
                        "[bold red]Failed to fetch issues from Jira.[/bold red]"
                    )
            except Exception as e:
                console.print(
                    f"[bold red]Error fetching issues from Jira: {str(e)}[/bold red]"
                )
                console.print(
                    "[bold yellow]Displaying existing data instead...[/bold yellow]"
                )

        # Display the data (either existing or newly updated)
        display_issues()
    else:
        # No data exists, fetch it
        console.print(
            "[bold yellow]No issues data found. Fetching from Jira...[/bold yellow]"
        )
        try:
            issue_ids = fetch_issue_ids()
            issues = fetch_issue_details(issue_ids)
            if issues:
                store_issues_in_db(issues)
                console.print(
                    "[bold green]Issues updated from Jira and stored in the database.[/bold green]"
                )
                display_issues()
            else:
                console.print(
                    "[bold red]Failed to fetch issues from Jira. No data to display.[/bold red]"
                )
                input("Press Enter to return to the menu...")
        except Exception as e:
            console.print(
                f"[bold red]Error fetching issues from Jira: {str(e)}[/bold red]"
            )
            console.print(
                "[bold red]Unable to fetch data. Please check your network connection and Jira configuration.[/bold red]"
            )
            input("Press Enter to return to the menu...")


def handle_commits_option():
    """Handle the unified commits option (get/update/display)."""
    if has_commits_data():
        # Data exists, ask if user wants to update
        update_choice = (
            console.input(
                "[bold yellow]Commits data already exists. Do you want to update it? (y/N): [/bold yellow]"
            )
            .strip()
            .lower()
        )

        if update_choice == "y" or update_choice == "yes":
            # User wants to update
            try:
                update_git_commits()
                console.print(
                    "[bold green]Commits since the earliest Jira ticket date have been stored in the database.[/bold green]"
                )
            except Exception as e:
                console.print(f"[bold red]Error updating commits: {str(e)}[/bold red]")
                console.print(
                    "[bold yellow]Displaying existing data instead...[/bold yellow]"
                )

        # Display the data (either existing or newly updated)
        display_commits()
    else:
        # No data exists, fetch it
        console.print(
            "[bold yellow]No commits data found. Fetching from repository...[/bold yellow]"
        )
        try:
            update_git_commits()
            console.print(
                "[bold green]Commits since the earliest Jira ticket date have been stored in the database.[/bold green]"
            )
            display_commits()
        except Exception as e:
            console.print(f"[bold red]Error fetching commits: {str(e)}[/bold red]")
            console.print(
                "[bold red]Unable to fetch commit data. Please check if you have Jira issues data first.[/bold red]"
            )
            input("Press Enter to return to the menu...")








def handle_daily_report_option():
    """Handle the daily activity report option (generate JSON with activity by time buckets)."""
    from datetime import datetime, date
    
    daily_report_file = "ux/web/data/daily_activity_report.json"
    
    # Ask user for target date
    console.print("\n[bold yellow]Daily Activity Report[/bold yellow]")
    console.print("[bold cyan]Enter target date (YYYY-MM-DD) or press Enter for today:[/bold cyan]")
    date_input = console.input("[bold green]Date: [/bold green]").strip()
    
    target_date = None
    if date_input:
        try:
            target_date = datetime.strptime(date_input, "%Y-%m-%d").date()
            console.print(f"[bold green]Generating report for: {target_date}[/bold green]")
        except ValueError:
            console.print("[bold red]Invalid date format. Using today instead.[/bold red]")
            target_date = None
    
    if target_date is None:
        target_date = datetime.now().date()
        console.print(f"[bold green]Generating report for today: {target_date}[/bold green]")
    
    # Check if report file already exists
    if os.path.exists(daily_report_file):
        # Data exists, ask if user wants to update
        update_choice = (
            console.input(
                "[bold yellow]Daily report file already exists. Do you want to regenerate it? (y/N): [/bold yellow]"
            )
            .strip()
            .lower()
        )

        if update_choice == "y" or update_choice == "yes":
            # User wants to regenerate
            try:
                json_filename = generate_daily_report_json(target_date)
                if not json_filename:
                    console.print(
                        "[bold red]Failed to generate daily report.[/bold red]"
                    )
                else:
                    console.print(
                        f"[bold green]Daily report generated successfully![/bold green]"
                    )
                    # Display the report
                    display_daily_report_summary(json_file=json_filename)
                input("Press Enter to return to the menu...")
            except Exception as e:
                console.print(
                    f"[bold red]Error generating daily report: {str(e)}[/bold red]"
                )
                import traceback
                traceback.print_exc()
                input("Press Enter to return to the menu...")
        else:
            # User wants to just display existing data
            try:
                display_daily_report_summary(json_file=daily_report_file)
                input("Press Enter to return to the menu...")
            except Exception as e:
                console.print(f"[bold red]Error displaying report: {str(e)}[/bold red]")
                input("Press Enter to return to the menu...")
    else:
        # No data exists, generate it
        console.print(
            "[bold yellow]No daily report file found. Generating from database...[/bold yellow]"
        )
        try:
            json_filename = generate_daily_report_json(target_date)
            if not json_filename:
                console.print(
                    "[bold red]Failed to generate daily report.[/bold red]"
                )
            else:
                console.print(
                    f"[bold green]Daily report generated successfully![/bold green]"
                )
                # Display the report
                display_daily_report_summary(json_file=json_filename)
            input("Press Enter to return to the menu...")
        except Exception as e:
            console.print(
                f"[bold red]Error generating daily report: {str(e)}[/bold red]"
            )
            import traceback
            traceback.print_exc()
            input("Press Enter to return to the menu...")





@cli.command()
def manage_issues():
    """Manage Jira issues."""
    while True:
        clear_screen()
        print_banner()

        console.print("[bold yellow]Choose an option:[/bold yellow]")
        console.print(
            "[bold cyan]1. Manage Jira issues (get/update/display)[/bold cyan]"
        )
        console.print(
            "[bold cyan]2. Manage git commits (get/update/display)[/bold cyan]"
        )
        console.print(
            "[bold cyan]3. Daily activity report JSON (generate/display)[/bold cyan]"
        )
        console.print("[bold cyan]4. Exit[/bold cyan]")

        choice = console.input(
            "[bold green]Enter your choice (1/2/3/4): [/bold green]"
        )

        if choice == "1":
            handle_issues_option()
        elif choice == "2":
            handle_commits_option()
        elif choice == "3":
            handle_daily_report_option()
        elif choice == "4":
            console.print("[bold red]Exiting SDM Tools.[/bold red]")
            break
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
            input("Press Enter to return to the menu...")


if __name__ == "__main__":
    cli()
