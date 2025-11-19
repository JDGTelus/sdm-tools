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


# ============================================================================
# NEW PHASE 2/3 HANDLERS - Normalized Database Functions
# ============================================================================

def handle_refresh_all_data():
    """Handle the complete data refresh workflow."""
    from .database import refresh_database_workflow
    
    console.print("\n[bold yellow]⚠️  WARNING: This will refresh ALL data from Jira and Git[/bold yellow]")
    console.print("[bold yellow]   - Current database will be backed up[/bold yellow]")
    console.print("[bold yellow]   - Fresh data will be fetched and normalized[/bold yellow]")
    console.print("[bold yellow]   - This may take several minutes[/bold yellow]\n")
    
    confirm = console.input("[bold red]Continue? (yes/N): [/bold red]").strip().lower()
    
    if confirm != "yes":
        console.print("[bold cyan]Refresh cancelled.[/bold cyan]")
        input("Press Enter to return to the menu...")
        return
    
    # Run the refresh workflow
    success = refresh_database_workflow()
    
    if success:
        console.print("\n[bold green]✓ Data refresh completed successfully![/bold green]")
    else:
        console.print("\n[bold red]✗ Data refresh failed. Check errors above.[/bold red]")
    
    input("\nPress Enter to return to the menu...")


def handle_view_sprints():
    """Display available sprints from the database."""
    from .database import get_available_sprints
    from rich.table import Table
    
    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]           AVAILABLE SPRINTS[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")
    
    sprints = get_available_sprints()
    
    if not sprints:
        console.print("[bold yellow]No sprints found. Please refresh data first.[/bold yellow]")
        input("\nPress Enter to return to the menu...")
        return
    
    # Create Rich table
    table = Table(show_header=True, header_style="bold cyan", border_style="cyan")
    table.add_column("ID", style="dim", width=8)
    table.add_column("Name", style="bold white", width=35)
    table.add_column("State", justify="center", width=10)
    table.add_column("Start Date", justify="center", width=12)
    table.add_column("End Date", justify="center", width=12)
    
    for sprint_id, name, state, start_date, end_date in sprints:
        # Color code by state
        if state == "active":
            state_colored = f"[bold green]{state}[/bold green]"
        elif state == "closed":
            state_colored = f"[dim]{state}[/dim]"
        else:
            state_colored = state
        
        table.add_row(
            str(sprint_id),
            name,
            state_colored,
            start_date or "N/A",
            end_date or "N/A"
        )
    
    console.print(table)
    console.print(f"\n[bold]Total sprints: {len(sprints)}[/bold]")
    
    input("\nPress Enter to return to the menu...")


def handle_view_developers():
    """Display active developers from the database."""
    from .database import get_active_developers
    from rich.table import Table
    
    console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]           ACTIVE DEVELOPERS[/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")
    
    developers = get_active_developers()
    
    if not developers:
        console.print("[bold yellow]No active developers found. Please refresh data first.[/bold yellow]")
        input("\nPress Enter to return to the menu...")
        return
    
    # Create Rich table
    table = Table(show_header=True, header_style="bold cyan", border_style="cyan")
    table.add_column("ID", style="dim", width=6)
    table.add_column("Name", style="bold white", width=35)
    table.add_column("Email", style="cyan", width=40)
    
    for dev_id, name, email in developers:
        table.add_row(str(dev_id), name, email)
    
    console.print(table)
    console.print(f"\n[bold]Total active developers: {len(developers)}[/bold]")
    console.print(f"[dim]Note: Active developers are those in INCLUDED_EMAILS configuration[/dim]")
    
    input("\nPress Enter to return to the menu...")


def handle_generate_reports():
    """Handle report generation submenu."""
    from .database.reports import (
        generate_daily_report_json,
        generate_sprint_report_json,
    )
    from .database.standalone import generate_standalone_report
    from .database import get_available_sprints
    from datetime import datetime, date
    
    while True:
        clear_screen()
        print_banner()
        
        console.print("[bold yellow]Generate Activity Report:[/bold yellow]\n")
        console.print("[bold cyan]1. Single day report (default: today)[/bold cyan]")
        console.print("[bold cyan]2. Full sprint report[/bold cyan]")
        console.print("[bold cyan]3. Generate standalone report (dist/)[/bold cyan]")
        console.print("[bold cyan]4. Generate bundled SPA report (dist/)[/bold cyan]")
        console.print("[bold cyan]5. Back to main menu[/bold cyan]")
        
        choice = console.input("\n[bold green]Enter your choice (1/2/3/4/5): [/bold green]").strip()
        
        if choice == "1":
            # Single day report
            date_input = console.input(
                "\n[bold yellow]Enter date (YYYY-MM-DD) or press Enter for today: [/bold yellow]"
            ).strip()
            
            if date_input:
                try:
                    target_date = datetime.strptime(date_input, "%Y-%m-%d").date()
                except ValueError:
                    console.print("[bold red]Invalid date format. Using today instead.[/bold red]")
                    target_date = None
            else:
                target_date = None
            
            # Generate report
            output = generate_daily_report_json(target_date)
            
            if output:
                console.print(f"\n[bold green]✓ Daily report ready![/bold green]")
                console.print(f"[dim]Open ux/web/daily-activity-dashboard.html to view[/dim]")
            
            input("\nPress Enter to continue...")
            
        elif choice == "2":
            # Sprint report - always generates last 10 sprints (or fewer if less available)
            sprints = get_available_sprints()
            
            if not sprints:
                console.print("\n[bold yellow]No sprints found. Please refresh data first.[/bold yellow]")
                input("\nPress Enter to continue...")
                continue
            
            # Show sprint count information
            sprint_count = len(sprints)
            limit = min(10, sprint_count)
            
            console.print("\n[bold cyan]Generating Sprint Activity Report...[/bold cyan]")
            if sprint_count < 10:
                console.print(f"[yellow]Found {sprint_count} sprint(s) (fewer than 10 available)[/yellow]")
            else:
                console.print(f"[dim]Processing last {limit} sprints[/dim]")
            
            # Show recent sprints that will be included
            console.print("\n[bold]Sprints to be included:[/bold]")
            for i, (sprint_id, name, state, start, end) in enumerate(sprints[:limit], 1):
                state_icon = "🟢" if state == "active" else "⚪"
                console.print(f"  {i}. {state_icon} {name} ({state})")
            
            # Generate multi-sprint report (always)
            output = generate_sprint_report_json()
            
            if output:
                console.print(f"\n[bold green]✓ Sprint report generated![/bold green]")
                console.print(f"[dim]File: {output}[/dim]")
                console.print(f"[dim]Open ux/web/sprint-activity-dashboard.html to view[/dim]")
            
            input("\nPress Enter to continue...")
            
        elif choice == "3":
            # Generate standalone report
            console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
            console.print("[bold cyan]        GENERATE STANDALONE REPORT[/bold cyan]")
            console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")
            
            console.print("[dim]This will create self-contained HTML files in dist/[/dim]")
            console.print("[dim]All data and styling will be inlined.[/dim]")
            console.print("[dim]Files will still require network access for CDN libraries.\n[/dim]")
            
            files = generate_standalone_report()
            
            if files:
                console.print(f"\n[bold green]✓ Standalone report(s) generated successfully![/bold green]\n")
                for f in files:
                    console.print(f"  [bold white]→ {f}[/bold white]")
                console.print(f"\n[dim]You can open these files directly in your browser.[/dim]")
            else:
                console.print("[bold red]Failed to generate standalone reports.[/bold red]")
            
            input("\nPress Enter to continue...")
            
        elif choice == "4":
            # Generate bundled SPA
            from .database.standalone import generate_bundle_spa
            
            console.print("\n[bold cyan]═══════════════════════════════════════════════[/bold cyan]")
            console.print("[bold cyan]        GENERATE BUNDLED SPA REPORT[/bold cyan]")
            console.print("[bold cyan]═══════════════════════════════════════════════[/bold cyan]\n")
            
            console.print("[dim]This will create a single-file SPA in dist/[/dim]")
            console.print("[dim]Includes side navigation to switch between reports.[/dim]")
            console.print("[dim]All data and styling will be inlined.[/dim]")
            console.print("[dim]Requires internet access for CDN libraries.\n[/dim]")
            
            bundle_file = generate_bundle_spa()
            
            if bundle_file:
                console.print(f"\n[bold green]✓ Bundled SPA generated successfully![/bold green]\n")
                console.print(f"  [bold white]→ {bundle_file}[/bold white]")
                console.print(f"\n[dim]Open this file directly in your browser.[/dim]")
                console.print(f"[dim]Use the sidebar to navigate between reports.[/dim]")
            else:
                console.print("[bold red]Failed to generate bundled SPA.[/bold red]")
            
            input("\nPress Enter to continue...")
            
        elif choice == "5":
            break
        else:
            console.print("[bold red]Invalid choice.[/bold red]")
            input("\nPress Enter to continue...")


def manage_issues_new():
    """Updated main menu with normalized database support."""
    while True:
        clear_screen()
        print_banner()

        console.print("[bold yellow]Choose an option:[/bold yellow]\n")
        console.print("[bold cyan]1. Refresh All Data (Jira + Git → Normalize)[/bold cyan]")
        console.print("[bold cyan]2. Generate Activity Reports[/bold cyan]")
        console.print("[bold cyan]3. View Sprints[/bold cyan]")
        console.print("[bold cyan]4. View Active Developers[/bold cyan]")
        console.print("[bold cyan]5. Exit[/bold cyan]")

        choice = console.input(
            "\n[bold green]Enter your choice (1/2/3/4/5): [/bold green]"
        )

        if choice == "1":
            handle_refresh_all_data()
        elif choice == "2":
            handle_generate_reports()
        elif choice == "3":
            handle_view_sprints()
        elif choice == "4":
            handle_view_developers()
        elif choice == "5":
            console.print("[bold red]Exiting SDM Tools.[/bold red]")
            break
        else:
            console.print("[bold red]Invalid choice. Please try again.[/bold red]")
            input("Press Enter to return to the menu...")


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """SDM Tools: Manage your team's Jira tasks with style!"""
    # Use new normalized database menu
    manage_issues_new()


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
    from .database.sprints import process_sprints_from_issues
    
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
                    # Process sprints after storing issues
                    process_sprints_from_issues(silent=False)
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
                # Process sprints after storing issues
                process_sprints_from_issues(silent=False)
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
