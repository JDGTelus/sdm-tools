"""Statistics generation functionality - Daily Activity Report."""

import json
import os
import shutil
import sqlite3
from datetime import datetime

from rich.console import Console
from rich.table import Table

from ..config import DB_NAME, INCLUDED_EMAILS, TABLE_NAME
from ..utils import (
    get_all_time_buckets,
    get_date_start_end,
    get_local_timezone,
    get_time_bucket,
    parse_git_date_to_local,
    parse_jira_date_to_local,
)

console = Console()


def extract_developer_info(assignee_json_str):
    """Extract name and email from the assignee JSON string."""
    try:
        import ast

        assignee_dict = ast.literal_eval(assignee_json_str)
        name = assignee_dict.get("displayName", "Unknown")
        email = assignee_dict.get("emailAddress", "Unknown")
        return name, email
    except:
        return assignee_json_str, "Unknown"


def should_include_email(email):
    """Check if an email should be included in the output."""
    if not email or email == "Unknown":
        return False

    # If no INCLUDED_EMAILS specified, include all (for backward compatibility)
    if not INCLUDED_EMAILS:
        return True

    # Clean up the included emails list (remove empty strings and whitespace)
    included_emails = [e.strip().lower() for e in INCLUDED_EMAILS if e.strip()]

    # Check if the email matches any included email (case-insensitive)
    return email.lower() in included_emails


# ============================================================================
# Daily Activity Report Functions
# ============================================================================


def get_daily_activity_by_buckets(target_date=None, tz=None):
    """Get developer activity by time buckets for a specific date.

    Time buckets:
        - "8am-10am": 08:00-09:59
        - "10am-12pm": 10:00-11:59
        - "12pm-2pm": 12:00-13:59
        - "2pm-4pm": 14:00-15:59
        - "4pm-6pm": 16:00-17:59
        - "off_hours": 18:00 previous day to 07:59 current day

    Args:
        target_date: date object or datetime object. If None, uses today.
        tz: Timezone string or ZoneInfo. If None, uses config TIMEZONE.

    Returns:
        Dict of developer email -> activity data with time buckets
    """
    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database does not exist.[/bold red]")
        return {}

    # Get timezone
    if tz is None:
        tz = get_local_timezone()
    elif isinstance(tz, str):
        tz = get_local_timezone(tz)

    # Get target date
    if target_date is None:
        target_date = datetime.now(tz).date()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()

    # Get date boundaries in local timezone
    date_start, date_end = get_date_start_end(target_date, tz)

    console.print(f"[bold cyan]Collecting daily activity for {target_date} ({tz})...[/bold cyan]")

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Initialize developer activity dict
        developer_activity = {}

        # Get list of included developers
        cursor.execute(
            f"""
            SELECT DISTINCT assignee
            FROM {TABLE_NAME}
            WHERE assignee IS NOT NULL AND assignee != '' AND assignee != 'null'
        """
        )
        assignees = [row[0] for row in cursor.fetchall()]

        # Filter to included emails only
        included_devs = {}
        for assignee in assignees:
            name, email = extract_developer_info(assignee)
            if should_include_email(email):
                included_devs[email.lower()] = (name, email)
                # Initialize developer in activity dict
                developer_activity[email.lower()] = {
                    "name": name,
                    "email": email,
                    "buckets": {
                        "8am-10am": {"jira": 0, "repo": 0, "total": 0},
                        "10am-12pm": {"jira": 0, "repo": 0, "total": 0},
                        "12pm-2pm": {"jira": 0, "repo": 0, "total": 0},
                        "2pm-4pm": {"jira": 0, "repo": 0, "total": 0},
                        "4pm-6pm": {"jira": 0, "repo": 0, "total": 0},
                    },
                    "off_hours": {"jira": 0, "repo": 0, "total": 0},
                    "daily_total": {"jira": 0, "repo": 0, "total": 0},
                }

        if not included_devs:
            console.print("[bold yellow]No developers in INCLUDED_EMAILS list.[/bold yellow]")
            return {}

        console.print(f"[bold green]Tracking {len(included_devs)} developers[/bold green]")

        # ===== COLLECT GIT COMMIT ACTIVITY =====
        # Check if git_commits table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'")
        if cursor.fetchone():
            cursor.execute("SELECT author_email, author_name, date FROM git_commits")
            commits = cursor.fetchall()

            for author_email, _author_name, commit_date_str in commits:
                if not author_email:
                    continue

                email_lower = author_email.lower()

                # Only process included developers
                if email_lower not in included_devs:
                    continue

                # Parse git date to local timezone
                local_dt = parse_git_date_to_local(commit_date_str, tz)
                if not local_dt:
                    continue

                # Check if commit is within target date
                if not (date_start <= local_dt <= date_end):
                    continue

                # Determine time bucket
                bucket = get_time_bucket(local_dt)

                # Add to appropriate bucket
                if bucket == "off_hours":
                    developer_activity[email_lower]["off_hours"]["repo"] += 1
                    developer_activity[email_lower]["off_hours"]["total"] += 1
                elif bucket:  # Regular bucket (10am-12pm, etc.)
                    developer_activity[email_lower]["buckets"][bucket]["repo"] += 1
                    developer_activity[email_lower]["buckets"][bucket]["total"] += 1

                # Add to daily total
                developer_activity[email_lower]["daily_total"]["repo"] += 1
                developer_activity[email_lower]["daily_total"]["total"] += 1

        # ===== COLLECT JIRA ACTIVITY =====
        # Get table columns
        cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
        columns = [info[1] for info in cursor.fetchall()]

        # Track Jira created events
        if "creator" in columns and "created" in columns:
            cursor.execute(
                f"""
                SELECT creator, created
                FROM {TABLE_NAME}
                WHERE creator IS NOT NULL AND created IS NOT NULL
            """
            )

            for creator, created_str in cursor.fetchall():
                if not creator:
                    continue

                _, email = extract_developer_info(creator)
                email_lower = email.lower()

                # Only process included developers
                if email_lower not in included_devs:
                    continue

                # Parse Jira date to local timezone
                local_dt = parse_jira_date_to_local(created_str, tz)
                if not local_dt:
                    continue

                # Check if event is within target date
                if not (date_start <= local_dt <= date_end):
                    continue

                # Determine time bucket
                bucket = get_time_bucket(local_dt)

                # Add to appropriate bucket
                if bucket == "off_hours":
                    developer_activity[email_lower]["off_hours"]["jira"] += 1
                    developer_activity[email_lower]["off_hours"]["total"] += 1
                elif bucket:
                    developer_activity[email_lower]["buckets"][bucket]["jira"] += 1
                    developer_activity[email_lower]["buckets"][bucket]["total"] += 1

                # Add to daily total
                developer_activity[email_lower]["daily_total"]["jira"] += 1
                developer_activity[email_lower]["daily_total"]["total"] += 1

        # Track Jira updated events
        if "assignee" in columns and "updated" in columns:
            cursor.execute(
                f"""
                SELECT assignee, updated
                FROM {TABLE_NAME}
                WHERE assignee IS NOT NULL AND updated IS NOT NULL
            """
            )

            for assignee, updated_str in cursor.fetchall():
                if not assignee:
                    continue

                _, email = extract_developer_info(assignee)
                email_lower = email.lower()

                # Only process included developers
                if email_lower not in included_devs:
                    continue

                # Parse Jira date to local timezone
                local_dt = parse_jira_date_to_local(updated_str, tz)
                if not local_dt:
                    continue

                # Check if event is within target date
                if not (date_start <= local_dt <= date_end):
                    continue

                # Determine time bucket
                bucket = get_time_bucket(local_dt)

                # Add to appropriate bucket
                if bucket == "off_hours":
                    developer_activity[email_lower]["off_hours"]["jira"] += 1
                    developer_activity[email_lower]["off_hours"]["total"] += 1
                elif bucket:
                    developer_activity[email_lower]["buckets"][bucket]["jira"] += 1
                    developer_activity[email_lower]["buckets"][bucket]["total"] += 1

                # Add to daily total
                developer_activity[email_lower]["daily_total"]["jira"] += 1
                developer_activity[email_lower]["daily_total"]["total"] += 1

        # Track Jira status change events
        if "assignee" in columns and "statuscategorychangedate" in columns:
            cursor.execute(
                f"""
                SELECT assignee, statuscategorychangedate
                FROM {TABLE_NAME}
                WHERE assignee IS NOT NULL AND statuscategorychangedate IS NOT NULL
            """
            )

            for assignee, status_date_str in cursor.fetchall():
                if not assignee:
                    continue

                _, email = extract_developer_info(assignee)
                email_lower = email.lower()

                # Only process included developers
                if email_lower not in included_devs:
                    continue

                # Parse Jira date to local timezone
                local_dt = parse_jira_date_to_local(status_date_str, tz)
                if not local_dt:
                    continue

                # Check if event is within target date
                if not (date_start <= local_dt <= date_end):
                    continue

                # Determine time bucket
                bucket = get_time_bucket(local_dt)

                # Add to appropriate bucket
                if bucket == "off_hours":
                    developer_activity[email_lower]["off_hours"]["jira"] += 1
                    developer_activity[email_lower]["off_hours"]["total"] += 1
                elif bucket:
                    developer_activity[email_lower]["buckets"][bucket]["jira"] += 1
                    developer_activity[email_lower]["buckets"][bucket]["total"] += 1

                # Add to daily total
                developer_activity[email_lower]["daily_total"]["jira"] += 1
                developer_activity[email_lower]["daily_total"]["total"] += 1

    console.print("[bold green]Daily activity collection complete![/bold green]")
    return developer_activity


def backup_daily_report_file(file_path):
    """Backup existing daily report file if it exists."""
    if os.path.exists(file_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        backup_path = os.path.join(directory, f"{name}_backup_{timestamp}{ext}")

        shutil.copy2(file_path, backup_path)
        console.print(f"[bold yellow]Backup created: {backup_path}[/bold yellow]")
        return backup_path
    return None


def generate_daily_report_json(target_date=None, output_file=None):
    """Generate daily activity report JSON file.

    Args:
        target_date: date object or datetime. If None, uses today.
        output_file: Path to output JSON file. If None, uses default location.

    Returns:
        Path to generated JSON file, or None if failed
    """
    # Default output file
    if output_file is None:
        output_file = "ux/web/data/daily_activity_report.json"

    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    # Get timezone
    tz = get_local_timezone()

    # Get target date
    if target_date is None:
        target_date = datetime.now(tz).date()
    elif isinstance(target_date, datetime):
        target_date = target_date.date()

    # Validate date is not in the future
    today = datetime.now(tz).date()
    if target_date > today:
        console.print(
            f"[bold red]Error: Cannot generate report for future date {target_date}[/bold red]"
        )
        console.print(
            f"[bold yellow]Today is {today}. Please select today or an earlier date.[/bold yellow]"
        )
        return None

    console.print(f"\n[bold cyan]Generating Daily Activity Report for {target_date}[/bold cyan]")

    # Collect activity data
    daily_activity = get_daily_activity_by_buckets(target_date, tz)

    if not daily_activity:
        console.print(
            "[bold red]No activity data collected. Aborting report generation.[/bold red]"
        )
        return None

    # Convert to list format for JSON
    developers_list = []
    for _email, data in daily_activity.items():
        developers_list.append(data)

    # Sort by total activity (descending)
    developers_list.sort(key=lambda d: d["daily_total"]["total"], reverse=True)

    # Calculate summary statistics
    total_developers = len(developers_list)
    total_activity = sum(d["daily_total"]["total"] for d in developers_list)
    total_jira = sum(d["daily_total"]["jira"] for d in developers_list)
    total_repo = sum(d["daily_total"]["repo"] for d in developers_list)

    # Find most active bucket
    bucket_totals = {}
    for bucket in get_all_time_buckets():
        if bucket == "off_hours":
            bucket_totals[bucket] = sum(d["off_hours"]["total"] for d in developers_list)
        else:
            bucket_totals[bucket] = sum(d["buckets"][bucket]["total"] for d in developers_list)

    most_active_bucket = (
        max(bucket_totals.items(), key=lambda x: x[1])[0] if bucket_totals else "N/A"
    )

    # Calculate off-hours percentage
    off_hours_total = bucket_totals.get("off_hours", 0)
    off_hours_percentage = (
        round((off_hours_total / total_activity * 100), 1) if total_activity > 0 else 0
    )

    # Build JSON structure
    report_data = {
        "generated_at": datetime.now(tz).isoformat(),
        "metadata": {
            "report_date": str(target_date),
            "timezone": str(tz),
            "time_buckets": ["8am-10am", "10am-12pm", "12pm-2pm", "2pm-4pm", "4pm-6pm"],
            "off_hours_window": "6pm previous day to 8am current day",
        },
        "developers": developers_list,
        "summary": {
            "total_developers": total_developers,
            "total_activity": total_activity,
            "total_jira_actions": total_jira,
            "total_repo_actions": total_repo,
            "most_active_bucket": most_active_bucket,
            "off_hours_activity": off_hours_total,
            "off_hours_percentage": off_hours_percentage,
            "bucket_totals": bucket_totals,
        },
    }

    # Backup existing file
    backup_daily_report_file(output_file)

    # Write JSON file
    try:
        with open(output_file, "w") as f:
            json.dump(report_data, f, indent=2)

        console.print("\n[bold green]Daily report generated successfully![/bold green]")
        console.print(f"[bold green]Output: {output_file}[/bold green]")

        # Display summary
        console.print("\n[bold cyan]Report Summary:[/bold cyan]")
        console.print(f"  Date: {target_date}")
        console.print(f"  Timezone: {tz}")
        console.print(f"  Total Developers: {total_developers}")
        console.print(f"  Total Activity: {total_activity}")
        console.print(f"  - Jira Actions: {total_jira}")
        console.print(f"  - Repo Actions: {total_repo}")
        console.print(
            f"  Most Active Bucket: {most_active_bucket} ({bucket_totals.get(most_active_bucket, 0)} actions)"
        )
        console.print(f"  Off-Hours Activity: {off_hours_total} ({off_hours_percentage}%)")

        return output_file

    except Exception as e:
        console.print(f"[bold red]Error writing JSON file: {e}[/bold red]")
        return None


def display_daily_report_summary(daily_activity_data=None, json_file=None):
    """Display daily activity report in a formatted Rich table.

    Args:
        daily_activity_data: Dict from get_daily_activity_by_buckets(), or None to load from JSON
        json_file: Path to JSON file to load. If None, uses default location.
    """
    # Load data from JSON if not provided
    if daily_activity_data is None:
        if json_file is None:
            json_file = "ux/web/data/daily_activity_report.json"

        if not os.path.exists(json_file):
            console.print(f"[bold red]Daily report file not found: {json_file}[/bold red]")
            console.print("[bold yellow]Generate it first using option 3.[/bold yellow]")
            return

        try:
            with open(json_file) as f:
                report_data = json.load(f)

            # Extract data from JSON structure
            metadata = report_data.get("metadata", {})
            developers_list = report_data.get("developers", [])
            summary = report_data.get("summary", {})

        except Exception as e:
            console.print(f"[bold red]Error loading JSON file: {e}[/bold red]")
            return
    else:
        # Convert dict to list format
        developers_list = list(daily_activity_data.values())
        developers_list.sort(key=lambda d: d["daily_total"]["total"], reverse=True)
        metadata = None
        summary = None

    if not developers_list:
        console.print("[bold yellow]No developer activity data to display.[/bold yellow]")
        return

    # Display header
    console.print(
        "\n[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]"
    )
    console.print(
        "[bold cyan]                    DAILY ACTIVITY REPORT                              [/bold cyan]"
    )
    console.print(
        "[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]"
    )

    if metadata:
        console.print(
            f"\n[bold yellow]Report Date:[/bold yellow] {metadata.get('report_date', 'N/A')}"
        )
        console.print(f"[bold yellow]Timezone:[/bold yellow] {metadata.get('timezone', 'N/A')}")
        console.print(
            f"[bold yellow]Generated:[/bold yellow] {report_data.get('generated_at', 'N/A')}\n"
        )

    # Create Rich table
    table = Table(
        show_header=True,
        header_style="bold cyan",
        title="Activity by Time Bucket",
        title_style="bold magenta",
        border_style="cyan",
    )

    # Add columns (cutoff times - max of each bucket)
    table.add_column("Developer", style="bold white", width=25)
    table.add_column("10am", justify="center", width=12)
    table.add_column("12pm", justify="center", width=12)
    table.add_column("2pm", justify="center", width=12)
    table.add_column("4pm", justify="center", width=12)
    table.add_column("6pm", justify="center", width=12)
    table.add_column("Off-Hours", justify="center", width=12, style="yellow")
    table.add_column("Total", justify="center", width=10, style="bold green")

    # Helper function to format cell with color based on activity level
    def format_cell(count, jira, repo):
        """Format cell with color coding based on activity level."""
        if count == 0:
            return "[dim]-[/dim]"
        elif count >= 10:
            color = "bold green"
        elif count >= 5:
            color = "green"
        elif count >= 3:
            color = "yellow"
        else:
            color = "white"

        return f"[{color}]{count}[/{color}] [dim]({jira}J/{repo}R)[/dim]"

    # Add rows for each developer (show top 15 most active)
    total_jira = 0
    total_repo = 0
    total_activity = 0
    bucket_totals = {
        "8am-10am": 0,
        "10am-12pm": 0,
        "12pm-2pm": 0,
        "2pm-4pm": 0,
        "4pm-6pm": 0,
        "off_hours": 0,
    }

    displayed_count = 0
    max_display = 15

    for dev in developers_list:
        if dev["daily_total"]["total"] == 0:
            continue  # Skip developers with no activity

        if displayed_count >= max_display:
            break

        name = dev["name"][:24]  # Truncate long names

        # Format each bucket
        bucket_8_10 = format_cell(
            dev["buckets"]["8am-10am"]["total"],
            dev["buckets"]["8am-10am"]["jira"],
            dev["buckets"]["8am-10am"]["repo"],
        )
        bucket_10_12 = format_cell(
            dev["buckets"]["10am-12pm"]["total"],
            dev["buckets"]["10am-12pm"]["jira"],
            dev["buckets"]["10am-12pm"]["repo"],
        )
        bucket_12_2 = format_cell(
            dev["buckets"]["12pm-2pm"]["total"],
            dev["buckets"]["12pm-2pm"]["jira"],
            dev["buckets"]["12pm-2pm"]["repo"],
        )
        bucket_2_4 = format_cell(
            dev["buckets"]["2pm-4pm"]["total"],
            dev["buckets"]["2pm-4pm"]["jira"],
            dev["buckets"]["2pm-4pm"]["repo"],
        )
        bucket_4_6 = format_cell(
            dev["buckets"]["4pm-6pm"]["total"],
            dev["buckets"]["4pm-6pm"]["jira"],
            dev["buckets"]["4pm-6pm"]["repo"],
        )
        off_hours = format_cell(
            dev["off_hours"]["total"], dev["off_hours"]["jira"], dev["off_hours"]["repo"]
        )

        total = f"[bold]{dev['daily_total']['total']}[/bold]"

        table.add_row(
            name, bucket_8_10, bucket_10_12, bucket_12_2, bucket_2_4, bucket_4_6, off_hours, total
        )

        # Accumulate totals
        total_jira += dev["daily_total"]["jira"]
        total_repo += dev["daily_total"]["repo"]
        total_activity += dev["daily_total"]["total"]
        bucket_totals["8am-10am"] += dev["buckets"]["8am-10am"]["total"]
        bucket_totals["10am-12pm"] += dev["buckets"]["10am-12pm"]["total"]
        bucket_totals["12pm-2pm"] += dev["buckets"]["12pm-2pm"]["total"]
        bucket_totals["2pm-4pm"] += dev["buckets"]["2pm-4pm"]["total"]
        bucket_totals["4pm-6pm"] += dev["buckets"]["4pm-6pm"]["total"]
        bucket_totals["off_hours"] += dev["off_hours"]["total"]

        displayed_count += 1

    # Add separator
    table.add_row(
        "─" * 24, "─" * 10, "─" * 10, "─" * 10, "─" * 10, "─" * 10, "─" * 10, "─" * 8, style="dim"
    )

    # Add totals row
    table.add_row(
        f"[bold cyan]TOTALS ({displayed_count} devs)[/bold cyan]",
        f"[bold]{bucket_totals['8am-10am']}[/bold]",
        f"[bold]{bucket_totals['10am-12pm']}[/bold]",
        f"[bold]{bucket_totals['12pm-2pm']}[/bold]",
        f"[bold]{bucket_totals['2pm-4pm']}[/bold]",
        f"[bold]{bucket_totals['4pm-6pm']}[/bold]",
        f"[bold yellow]{bucket_totals['off_hours']}[/bold yellow]",
        f"[bold green]{total_activity}[/bold green]",
    )

    # Display table
    console.print(table)

    # Display legend
    console.print("\n[bold]Legend:[/bold] [dim](J=Jira, R=Repo)[/dim]")
    console.print(
        "[bold green]■[/bold green] High (10+)  [green]■[/green] Medium (5-9)  [yellow]■[/yellow] Low (3-4)  [white]■[/white] Minimal (1-2)"
    )

    # Display summary statistics
    if summary:
        console.print("\n[bold cyan]Summary Statistics:[/bold cyan]")
        console.print(f"  Total Developers: {summary.get('total_developers', 'N/A')}")
        console.print(f"  Total Activity: {summary.get('total_activity', total_activity)}")
        console.print(f"  - Jira Actions: {summary.get('total_jira_actions', total_jira)}")
        console.print(f"  - Repo Actions: {summary.get('total_repo_actions', total_repo)}")
        console.print(
            f"  Most Active Bucket: [bold]{summary.get('most_active_bucket', 'N/A')}[/bold]"
        )
        console.print(
            f"  Off-Hours Activity: {summary.get('off_hours_activity', 0)} ({summary.get('off_hours_percentage', 0)}%)"
        )
    else:
        console.print("\n[bold cyan]Summary Statistics:[/bold cyan]")
        console.print(f"  Displayed Developers: {displayed_count}")
        console.print(f"  Total Activity: {total_activity}")
        console.print(f"  - Jira Actions: {total_jira}")
        console.print(f"  - Repo Actions: {total_repo}")

    if displayed_count < len(developers_list):
        remaining = len(developers_list) - displayed_count
        console.print(f"\n[dim]Note: {remaining} developers with no activity not shown[/dim]")

    console.print(
        "\n[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]\n"
    )
