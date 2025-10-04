"""CLI handler"""
import os
import sqlite3
import click
from .utils import clear_screen, print_banner, console
from .jira import fetch_issue_ids, fetch_issue_details
from .database import (
    store_issues_in_db, display_issues, update_git_commits, display_commits,
    generate_sprint_stats_json, display_existing_sprint_stats,
    generate_developer_activity_json
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
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
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
            "SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'")
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
        update_choice = console.input(
            "[bold yellow]Issues data already exists. Do you want to update it? (y/N): [/bold yellow]").strip().lower()

        if update_choice == 'y' or update_choice == 'yes':
            # User wants to update
            try:
                issue_ids = fetch_issue_ids()
                issues = fetch_issue_details(issue_ids)
                if issues:
                    store_issues_in_db(issues)
                    console.print(
                        "[bold green]Issues updated from Jira and stored in the database.[/bold green]")
                else:
                    console.print(
                        "[bold red]Failed to fetch issues from Jira.[/bold red]")
            except Exception as e:
                console.print(
                    f"[bold red]Error fetching issues from Jira: {str(e)}[/bold red]")
                console.print(
                    "[bold yellow]Displaying existing data instead...[/bold yellow]")

        # Display the data (either existing or newly updated)
        display_issues()
    else:
        # No data exists, fetch it
        console.print(
            "[bold yellow]No issues data found. Fetching from Jira...[/bold yellow]")
        try:
            issue_ids = fetch_issue_ids()
            issues = fetch_issue_details(issue_ids)
            if issues:
                store_issues_in_db(issues)
                console.print(
                    "[bold green]Issues updated from Jira and stored in the database.[/bold green]")
                display_issues()
            else:
                console.print(
                    "[bold red]Failed to fetch issues from Jira. No data to display.[/bold red]")
                input("Press Enter to return to the menu...")
        except Exception as e:
            console.print(
                f"[bold red]Error fetching issues from Jira: {str(e)}[/bold red]")
            console.print(
                "[bold red]Unable to fetch data. Please check your network connection and Jira configuration.[/bold red]")
            input("Press Enter to return to the menu...")


def handle_commits_option():
    """Handle the unified commits option (get/update/display)."""
    if has_commits_data():
        # Data exists, ask if user wants to update
        update_choice = console.input(
            "[bold yellow]Commits data already exists. Do you want to update it? (y/N): [/bold yellow]").strip().lower()

        if update_choice == 'y' or update_choice == 'yes':
            # User wants to update
            try:
                update_git_commits()
                console.print(
                    "[bold green]Commits since the earliest Jira ticket date have been stored in the database.[/bold green]")
            except Exception as e:
                console.print(
                    f"[bold red]Error updating commits: {str(e)}[/bold red]")
                console.print(
                    "[bold yellow]Displaying existing data instead...[/bold yellow]")

        # Display the data (either existing or newly updated)
        display_commits()
    else:
        # No data exists, fetch it
        console.print(
            "[bold yellow]No commits data found. Fetching from repository...[/bold yellow]")
        try:
            update_git_commits()
            console.print(
                "[bold green]Commits since the earliest Jira ticket date have been stored in the database.[/bold green]")
            display_commits()
        except Exception as e:
            console.print(
                f"[bold red]Error fetching commits: {str(e)}[/bold red]")
            console.print(
                "[bold red]Unable to fetch commit data. Please check if you have Jira issues data first.[/bold red]")
            input("Press Enter to return to the menu...")


def handle_sprint_analytics_option():
    """Handle the sprint analytics option (display or generate JSON with sprint stats)."""
    sprint_stats_file = "ux/web/data/team_sprint_stats.json"

    # Check if sprint stats file already exists
    if os.path.exists(sprint_stats_file):
        # Data exists, ask if user wants to update or just display
        update_choice = console.input(
            "[bold yellow]Sprint analytics file already exists. Do you want to update it? (y/N): [/bold yellow]").strip().lower()

        if update_choice == 'y' or update_choice == 'yes':
            # User wants to update
            console.print(
                "[bold yellow]Generating updated sprint analytics from Jira issues, git commits, and sprint data...[/bold yellow]")
            try:
                json_filename = generate_sprint_stats_json()
                if not json_filename:
                    console.print(
                        "[bold red]Failed to generate sprint analytics.[/bold red]")
                    input("Press Enter to return to the menu...")
            except Exception as e:
                console.print(
                    f"[bold red]Error generating sprint analytics: {str(e)}[/bold red]")
                input("Press Enter to return to the menu...")
        else:
            # User wants to just display existing data
            try:
                display_existing_sprint_stats()
            except Exception as e:
                console.print(
                    f"[bold red]Error displaying existing sprint analytics: {str(e)}[/bold red]")
                input("Press Enter to return to the menu...")
    else:
        # No data exists, generate it
        console.print(
            "[bold yellow]No sprint analytics file found. Generating from Jira issues, git commits, and sprint data...[/bold yellow]")
        try:
            json_filename = generate_sprint_stats_json()
            if not json_filename:
                console.print(
                    "[bold red]Failed to generate sprint analytics.[/bold red]")
                input("Press Enter to return to the menu...")
        except Exception as e:
            console.print(
                f"[bold red]Error generating sprint analytics: {str(e)}[/bold red]")
            input("Press Enter to return to the menu...")


def handle_developer_activity_option():
    """Handle the developer activity option (generate JSON with activity by sprint and last 3 days)."""
    activity_file = "ux/web/data/developer_activity.json"

    # Check if activity file already exists
    if os.path.exists(activity_file):
        # Data exists, ask if user wants to update or just display
        update_choice = console.input(
            "[bold yellow]Developer activity file already exists. Do you want to update it? (y/N): [/bold yellow]").strip().lower()

        if update_choice == 'y' or update_choice == 'yes':
            # User wants to update
            console.print(
                "[bold yellow]Generating updated developer activity from Jira issues, git commits, and sprint data...[/bold yellow]")
            try:
                json_filename = generate_developer_activity_json()
                if not json_filename:
                    console.print(
                        "[bold red]Failed to generate developer activity.[/bold red]")
                    input("Press Enter to return to the menu...")
            except Exception as e:
                console.print(
                    f"[bold red]Error generating developer activity: {str(e)}[/bold red]")
                import traceback
                traceback.print_exc()
                input("Press Enter to return to the menu...")
        else:
            # User wants to just display existing data - show summary
            console.print(
                f"[bold green]Developer activity file exists at: {activity_file}[/bold green]")
            console.print(
                "[bold yellow]Use option 4 to generate HTML dashboard from this data.[/bold yellow]")
            input("Press Enter to return to the menu...")
    else:
        # No data exists, generate it
        console.print(
            "[bold yellow]No developer activity file found. Generating from Jira issues, git commits, and sprint data...[/bold yellow]")
        try:
            json_filename = generate_developer_activity_json()
            if not json_filename:
                console.print(
                    "[bold red]Failed to generate developer activity.[/bold red]")
                input("Press Enter to return to the menu...")
        except Exception as e:
            console.print(
                f"[bold red]Error generating developer activity: {str(e)}[/bold red]")
            import traceback
            traceback.print_exc()
            input("Press Enter to return to the menu...")


def handle_html_generation_option():
    """Handle the HTML generation option - creates self-sufficient HTML dashboards for all HTML files in ux/web."""
    import json
    import glob
    from datetime import datetime
    import shutil

    console.print(
        "[bold yellow]Generating self-sufficient HTML dashboards...[/bold yellow]")

    try:
        # Create dist directory
        dist_dir = "dist"
        if not os.path.exists(dist_dir):
            os.makedirs(dist_dir)
            console.print(
                f"[bold green]Created {dist_dir} directory.[/bold green]")

        # Read the CSS file once
        css_file = "ux/web/shared-dashboard-styles.css"
        if not os.path.exists(css_file):
            console.print(
                f"[bold red]CSS file not found at {css_file}.[/bold red]")
            input("Press Enter to return to the menu...")
            return

        with open(css_file, 'r', encoding='utf-8') as f:
            css_content = f.read()

        # Find all HTML files in ux/web directory
        html_files = glob.glob("ux/web/*.html")

        if not html_files:
            console.print(
                "[bold red]No HTML files found in ux/web directory.[/bold red]")
            input("Press Enter to return to the menu...")
            return

        generated_files = []

        for html_file in html_files:
            try:
                # Extract filename without path
                filename = os.path.basename(html_file)
                console.print(
                    f"[bold cyan]Processing {filename}...[/bold cyan]")

                # Determine which JSON file to use based on HTML filename
                json_file = None
                if "activity" in filename.lower():
                    json_file = "ux/web/data/developer_activity.json"
                elif "sprint" in filename.lower():
                    json_file = "ux/web/data/team_sprint_stats.json"
                elif "basic" in filename.lower():
                    json_file = "ux/web/data/team_basic_stats.json"
                elif "simple" in filename.lower():
                    json_file = "ux/web/data/team_simple_stats.json"
                else:
                    # Default to sprint stats if no specific pattern matches
                    json_file = "ux/web/data/team_sprint_stats.json"

                if not os.path.exists(json_file):
                    console.print(
                        f"[bold yellow]Skipping {filename} - Data file not found at {json_file}.[/bold yellow]")
                    continue

                # Define the target filename
                target_file = os.path.join(dist_dir, filename)

                # If target file exists, create a timestamped backup
                if os.path.exists(target_file):
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    backup_file = os.path.join(
                        dist_dir, f"{os.path.splitext(filename)[0]}_{timestamp}.html")
                    shutil.move(target_file, backup_file)
                    console.print(
                        f"[bold yellow]Existing file backed up as: {backup_file}[/bold yellow]")

                # Read the JSON data
                with open(json_file, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)

                # Read the HTML template
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()

                # Replace the CSS import with inline styles
                inline_css = f'<style>\n{css_content}\n</style>'
                html_content = html_content.replace(
                    '<link rel="stylesheet" href="shared-dashboard-styles.css">', inline_css)

                # Replace the fetch call with embedded data
                # Use more indentation for readability
                json_str = json.dumps(json_data, indent=8)

                # Find the useEffect block and replace the entire fetch logic
                useEffect_start = html_content.find("useEffect(() => {")
                if useEffect_start != -1:
                    # Find the end of the useEffect block
                    useEffect_end = html_content.find(
                        "}, []);", useEffect_start)
                    if useEffect_end != -1:
                        useEffect_end += len("}, []);")

                        # Determine the state setter function name based on the HTML content
                        if "setData(" in html_content:
                            state_setter = "setData"
                        elif "setTeamData(" in html_content:
                            state_setter = "setTeamData"
                        else:
                            state_setter = "setData"  # Default

                        # Create the new useEffect content with embedded data
                        new_useEffect = f"""useEffect(() => {{
            // Data embedded directly in the HTML
            {state_setter}({json_str});
            setLoading(false);
        }}, []);"""

                        # Replace the entire useEffect block
                        html_content = (html_content[:useEffect_start] +
                                        new_useEffect +
                                        html_content[useEffect_end:])

                # Write the combined HTML file
                with open(target_file, 'w', encoding='utf-8') as f:
                    f.write(html_content)

                generated_files.append(target_file)
                console.print(
                    f"[bold green]✓ Generated: {target_file}[/bold green]")

            except Exception as e:
                console.print(
                    f"[bold red]Error processing {filename}: {str(e)}[/bold red]")

        if generated_files:
            console.print(
                f"[bold green]Successfully generated {len(generated_files)} self-sufficient HTML dashboard(s)![/bold green]")
            for file in generated_files:
                console.print(f"[bold cyan]  • {file}[/bold cyan]")
            console.print(
                f"[bold yellow]These files contain all data and styles embedded and can be opened directly in any browser.[/bold yellow]")
        else:
            console.print(
                "[bold red]No dashboards were generated. Please ensure JSON data files exist.[/bold red]")

    except Exception as e:
        console.print(
            f"[bold red]Error generating HTML dashboards: {str(e)}[/bold red]")

    input("Press Enter to return to the menu...")


@cli.command()
def manage_issues():
    """Manage Jira issues."""
    while True:
        clear_screen()
        print_banner()

        console.print("[bold yellow]Choose an option:[/bold yellow]")
        console.print(
            "[bold cyan]1. Manage Jira issues (get/update/display)[/bold cyan]")
        console.print(
            "[bold cyan]2. Manage git commits (get/update/display)[/bold cyan]")
        console.print(
            "[bold cyan]3. Team sprint analytics JSON (update/display)[/bold cyan]")
        console.print(
            "[bold cyan]4. Developer activity JSON (update/display)[/bold cyan]")
        console.print(
            "[bold cyan]5. Generate self-sufficient HTML dashboard[/bold cyan]")
        console.print("[bold cyan]6. Exit[/bold cyan]")

        choice = console.input(
            "[bold green]Enter your choice (1/2/3/4/5/6): [/bold green]")

        if choice == '1':
            handle_issues_option()
        elif choice == '2':
            handle_commits_option()
        elif choice == '3':
            handle_sprint_analytics_option()
        elif choice == '4':
            handle_developer_activity_option()
        elif choice == '5':
            handle_html_generation_option()
        elif choice == '6':
            console.print("[bold red]Exiting SDM Tools.[/bold red]")
            break
        else:
            console.print(
                "[bold red]Invalid choice. Please try again.[/bold red]")
            input("Press Enter to return to the menu...")


if __name__ == "__main__":
    cli()
