"""Statistics generation functionality."""

import os
import sqlite3
import json
import shutil
from datetime import datetime, date
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from ..config import DB_NAME, TABLE_NAME, BASIC_STATS, INCLUDED_EMAILS, TIMEZONE
from ..utils import (
    parse_git_date_to_local,
    parse_jira_date_to_local,
    get_time_bucket,
    get_date_start_end,
    get_all_time_buckets,
    is_off_hours,
    get_local_timezone
)

console = Console()


def extract_issue_code_from_watches(watches_data):
    """Extract issue code (SET-XXXXX) from watches field JSON data."""
    if not watches_data:
        return None

    try:
        # Parse the JSON string (it's stored as a string representation of a Python dict)
        import ast

        watches_dict = ast.literal_eval(watches_data)

        # Extract the 'self' URL
        if "self" in watches_dict:
            url = watches_dict["self"]
            # Split by '/' and get the part before '/watchers'
            parts = url.split("/")
            if len(parts) >= 2:
                # Look for the issue code in the URL path
                for part in parts:
                    if part.startswith("SET-") and len(part) > 4:
                        # Validate it looks like SET-XXXXX format (SET- followed by digits)
                        # Get part after 'SET-'
                        issue_part = part.split("-", 1)[1]
                        if issue_part.isdigit():
                            return part
    except (ValueError, AttributeError, TypeError, SyntaxError) as e:
        # If parsing fails, return None
        pass

    return None


def backup_existing_stats_file():
    """Backup existing basic stats file if it exists."""
    if os.path.exists(BASIC_STATS):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Ensure backup is created in the same directory as the stats file
        stats_dir = os.path.dirname(BASIC_STATS)
        backup_filename = os.path.join(
            stats_dir, f"team_basic_stats_backup_{timestamp}.json"
        )
        shutil.copy2(BASIC_STATS, backup_filename)
        console.print(
            f"[bold yellow]Existing basic stats file backed up to: {backup_filename}[/bold yellow]"
        )
        return backup_filename
    return None


def backup_existing_developer_stats_file():
    """Backup existing developer stats file if it exists."""
    from ..config import SIMPLE_STATS

    if os.path.exists(SIMPLE_STATS):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Ensure backup is created in the same directory as the stats file
        stats_dir = os.path.dirname(SIMPLE_STATS)
        backup_filename = os.path.join(
            stats_dir, f"team_simple_stats_backup_{timestamp}.json"
        )
        shutil.copy2(SIMPLE_STATS, backup_filename)
        console.print(
            f"[bold yellow]Existing developer stats file backed up to: {backup_filename}[/bold yellow]"
        )
        return backup_filename
    return None


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


def get_jira_stats_for_assignee(cursor, assignee):
    """Get Jira statistics for a specific assignee."""
    stats = {}

    # Total issues assigned
    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE assignee = ?", (assignee,))
    stats["total_issues"] = cursor.fetchone()[0]

    # Issues by status
    cursor.execute(
        f"""
        SELECT status, COUNT(*)
        FROM {TABLE_NAME}
        WHERE assignee = ?
        GROUP BY status
    """,
        (assignee,),
    )
    status_counts = dict(cursor.fetchall())
    stats["issues_by_status"] = status_counts

    # Check what columns are available
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    # Issues by priority (if priority field exists)
    if "priority" in columns:
        cursor.execute(
            f"""
            SELECT priority, COUNT(*)
            FROM {TABLE_NAME}
            WHERE assignee = ? AND priority IS NOT NULL AND priority != ''
            GROUP BY priority
        """,
            (assignee,),
        )
        priority_counts = dict(cursor.fetchall())
        stats["issues_by_priority"] = priority_counts

    # Total story points (if customfield_10026 exists)
    if "customfield_10026" in columns:
        cursor.execute(
            f"""
            SELECT SUM(CAST(customfield_10026 AS REAL))
            FROM {TABLE_NAME}
            WHERE assignee = ? AND customfield_10026 IS NOT NULL AND customfield_10026 != ''
        """,
            (assignee,),
        )
        result = cursor.fetchone()[0]
        stats["total_story_points"] = round(result, 1) if result else 0

    # Story points by status (if customfield_10026 exists)
    if "customfield_10026" in columns:
        cursor.execute(
            f"""
            SELECT status, SUM(CAST(customfield_10026 AS REAL))
            FROM {TABLE_NAME}
            WHERE assignee = ? AND customfield_10026 IS NOT NULL AND customfield_10026 != ''
            GROUP BY status
        """,
            (assignee,),
        )
        story_points_by_status = dict(cursor.fetchall())
        # Round the values
        stats["story_points_by_status"] = {
            k: round(v, 1) if v else 0 for k, v in story_points_by_status.items()
        }

    # Issues by label (if customfield_10014 exists)
    if "customfield_10014" in columns:
        cursor.execute(
            f"""
            SELECT customfield_10014, COUNT(*)
            FROM {TABLE_NAME}
            WHERE assignee = ? AND customfield_10014 IS NOT NULL AND customfield_10014 != ''
            GROUP BY customfield_10014
        """,
            (assignee,),
        )
        label_counts = dict(cursor.fetchall())
        stats["issues_by_label"] = label_counts

    # Extract issue codes from watches field (if watches field exists)
    if "watches" in columns:
        cursor.execute(
            f"""
            SELECT watches
            FROM {TABLE_NAME}
            WHERE assignee = ? AND watches IS NOT NULL AND watches != ''
        """,
            (assignee,),
        )
        watches_data = cursor.fetchall()

        issue_codes = []
        for (watches_json,) in watches_data:
            issue_code = extract_issue_code_from_watches(watches_json)
            if issue_code:
                issue_codes.append(issue_code)

        stats["issue_codes"] = issue_codes

    # Average time in status (if created and updated fields exist)
    if "created" in columns and "updated" in columns:
        cursor.execute(
            f"""
            SELECT created, updated
            FROM {TABLE_NAME}
            WHERE assignee = ? AND created IS NOT NULL AND updated IS NOT NULL
        """,
            (assignee,),
        )
        dates = cursor.fetchall()
        if dates:
            total_days = 0
            valid_dates = 0
            for created, updated in dates:
                try:
                    created_date = datetime.strptime(created, "%Y-%m-%dT%H:%M:%S.%f%z")
                    updated_date = datetime.strptime(updated, "%Y-%m-%dT%H:%M:%S.%f%z")
                    days_diff = (updated_date - created_date).days
                    if days_diff >= 0:
                        total_days += days_diff
                        valid_dates += 1
                except:
                    continue

            if valid_dates > 0:
                stats["avg_days_to_update"] = round(total_days / valid_dates, 2)

    return stats


def get_git_stats_for_assignee(cursor, assignee):
    """Get Git statistics for a specific assignee by matching email or name."""
    stats = {}

    # Extract email from assignee JSON if possible
    try:
        import ast

        assignee_dict = ast.literal_eval(assignee)
        assignee_email = assignee_dict.get("emailAddress", "")
        assignee_name = assignee_dict.get("displayName", "")
    except:
        assignee_email = ""
        assignee_name = assignee

    # Try to find commits by matching assignee email or name with author_email or author_name
    search_patterns = []
    if assignee_email:
        search_patterns.append(assignee_email)
    if assignee_name:
        search_patterns.append(assignee_name)

    total_commits = 0
    matching_authors = []

    for pattern in search_patterns:
        cursor.execute(
            """
            SELECT COUNT(*), author_name, author_email
            FROM git_commits
            WHERE author_name LIKE ? OR author_email LIKE ?
            GROUP BY author_name, author_email
        """,
            (f"%{pattern}%", f"%{pattern}%"),
        )

        matches = cursor.fetchall()
        for count, name, email in matches:
            # Avoid duplicates
            if not any(author["email"] == email for author in matching_authors):
                total_commits += count
                matching_authors.append(
                    {"name": name, "email": email, "commits": count}
                )

    stats["total_commits"] = total_commits
    stats["matching_git_authors"] = matching_authors

    # Get commit frequency (commits per day) for all matching authors
    if matching_authors:
        all_emails = [author["email"] for author in matching_authors]
        placeholders = ",".join(["?" for _ in all_emails])
        cursor.execute(
            f"""
            SELECT date
            FROM git_commits
            WHERE author_email IN ({placeholders})
            ORDER BY date
        """,
            all_emails,
        )

        commit_dates = [row[0] for row in cursor.fetchall()]
        if len(commit_dates) > 1:
            try:
                first_commit = datetime.strptime(commit_dates[0].split()[0], "%Y-%m-%d")
                last_commit = datetime.strptime(commit_dates[-1].split()[0], "%Y-%m-%d")
                days_active = (last_commit - first_commit).days + 1
                stats["commits_per_day"] = (
                    round(total_commits / days_active, 2) if days_active > 0 else 0
                )
                stats["days_active"] = days_active
            except:
                pass

    return stats


def calculate_combined_stats(jira_stats, git_stats):
    """Calculate combined statistics from Jira and Git data."""
    combined = {}

    # Productivity score (simple calculation)
    jira_score = jira_stats.get("total_issues", 0) * 10
    git_score = git_stats.get("total_commits", 0) * 2
    combined["productivity_score"] = jira_score + git_score

    # Activity ratio (commits per issue)
    total_issues = jira_stats.get("total_issues", 0)
    total_commits = git_stats.get("total_commits", 0)

    if total_issues > 0:
        combined["commits_per_issue"] = round(total_commits / total_issues, 2)
    else:
        combined["commits_per_issue"] = 0

    # Status completion rate
    status_counts = jira_stats.get("issues_by_status", {})
    total_jira_issues = sum(status_counts.values()) if status_counts else 0

    # Common "done" status indicators
    done_statuses = ["Done", "Closed", "Resolved", "Complete", "Completed"]
    done_count = sum(status_counts.get(status, 0) for status in done_statuses)

    if total_jira_issues > 0:
        combined["completion_rate"] = round((done_count / total_jira_issues) * 100, 2)
    else:
        combined["completion_rate"] = 0

    return combined


def generate_summary_stats(developer_stats):
    """Generate summary statistics across all developers."""
    summary = {
        "total_developers": len(developer_stats),
        "total_issues": sum(
            dev["jira_stats"].get("total_issues", 0) for dev in developer_stats.values()
        ),
        "total_commits": sum(
            dev["git_stats"].get("total_commits", 0) for dev in developer_stats.values()
        ),
        "avg_productivity_score": 0,
        "avg_completion_rate": 0,
        "top_performers": [],
    }

    if developer_stats:
        # Calculate averages
        productivity_scores = [
            dev["combined_stats"].get("productivity_score", 0)
            for dev in developer_stats.values()
        ]
        completion_rates = [
            dev["combined_stats"].get("completion_rate", 0)
            for dev in developer_stats.values()
        ]

        summary["avg_productivity_score"] = round(
            sum(productivity_scores) / len(productivity_scores), 2
        )
        summary["avg_completion_rate"] = round(
            sum(completion_rates) / len(completion_rates), 2
        )

        # Top performers by productivity score
        sorted_devs = sorted(
            developer_stats.items(),
            key=lambda x: x[1]["combined_stats"].get("productivity_score", 0),
            reverse=True,
        )

        summary["top_performers"] = [
            {
                "name": name,
                "productivity_score": stats["combined_stats"].get(
                    "productivity_score", 0
                ),
                "total_issues": stats["jira_stats"].get("total_issues", 0),
                "total_commits": stats["git_stats"].get("total_commits", 0),
            }
            for name, stats in sorted_devs[:5]  # Top 5
        ]

    return summary


def display_developer_stats_summary(developer_stats):
    """Display a summary table of developer statistics with cleaner format."""
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Developer")
    table.add_column("Email")
    table.add_column("Issues")
    table.add_column("Commits")
    table.add_column("Productivity Score")
    table.add_column("Completion Rate %")
    table.add_column("Commits/Issue")

    for assignee_json, stats in developer_stats.items():
        jira_stats = stats["jira_stats"]
        git_stats = stats["git_stats"]
        combined_stats = stats["combined_stats"]

        # Extract clean name and email for display
        name, email = extract_developer_info(assignee_json)

        table.add_row(
            name,
            email,
            str(jira_stats.get("total_issues", 0)),
            str(git_stats.get("total_commits", 0)),
            str(combined_stats.get("productivity_score", 0)),
            f"{combined_stats.get('completion_rate', 0)}%",
            str(combined_stats.get("commits_per_issue", 0)),
        )

    console.print("\n[bold yellow]Developer Statistics Summary:[/bold yellow]")
    console.print(table)


def get_time_based_commit_stats(cursor, assignee):
    """Get commit statistics for specific time periods."""
    from datetime import datetime, timedelta
    import re

    stats = {"last_1_day": 0, "last_3_days": 0, "last_7_days": 0}

    # Extract email from assignee JSON if possible
    try:
        import ast

        assignee_dict = ast.literal_eval(assignee)
        assignee_email = assignee_dict.get("emailAddress", "")
        assignee_name = assignee_dict.get("displayName", "")
    except:
        assignee_email = ""
        assignee_name = assignee

    # Calculate date thresholds
    now = datetime.now()
    one_day_ago = now - timedelta(days=1)
    three_days_ago = now - timedelta(days=3)
    seven_days_ago = now - timedelta(days=7)

    # Get all commits for this assignee first, then filter by date
    search_conditions = []
    search_params = []

    if assignee_email:
        search_conditions.append("author_email = ?")
        search_params.append(assignee_email)
    if assignee_name:
        search_conditions.append("author_name = ?")
        search_params.append(assignee_name)

    if not search_conditions:
        return stats

    # Use OR to combine conditions, but avoid double counting
    where_clause = " OR ".join(search_conditions)

    cursor.execute(
        f"""
        SELECT DISTINCT date
        FROM git_commits
        WHERE {where_clause}
    """,
        search_params,
    )

    commit_dates = cursor.fetchall()

    for (date_str,) in commit_dates:
        try:
            # Parse git date format: "Wed Sep 17 23:37:12 2025 +0000"
            # Remove timezone info and parse
            date_clean = re.sub(r"\s+[+-]\d{4}$", "", date_str)
            commit_date = datetime.strptime(date_clean, "%a %b %d %H:%M:%S %Y")

            # Count commits for each time period
            if commit_date >= one_day_ago:
                stats["last_1_day"] += 1
            if commit_date >= three_days_ago:
                stats["last_3_days"] += 1
            if commit_date >= seven_days_ago:
                stats["last_7_days"] += 1

        except (ValueError, AttributeError) as e:
            # Skip commits with unparseable dates
            console.print(
                f"[bold yellow]Warning: Could not parse date '{date_str}': {e}[/bold yellow]"
            )
            continue

    return stats


def get_time_based_jira_stats(cursor, assignee):
    """Get Jira update statistics for specific time periods."""
    from datetime import datetime, timedelta

    stats = {"last_1_day": 0, "last_3_days": 0, "last_7_days": 0}

    # Calculate date thresholds
    now = datetime.now()
    one_day_ago = (now - timedelta(days=1)).isoformat()
    three_days_ago = (now - timedelta(days=3)).isoformat()
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    # Check if updated column exists
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if "updated" in columns:
        # Last 1 day
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {TABLE_NAME}
            WHERE assignee = ? AND updated >= ?
        """,
            (assignee, one_day_ago),
        )
        stats["last_1_day"] = cursor.fetchone()[0]

        # Last 3 days
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {TABLE_NAME}
            WHERE assignee = ? AND updated >= ?
        """,
            (assignee, three_days_ago),
        )
        stats["last_3_days"] = cursor.fetchone()[0]

        # Last 7 days
        cursor.execute(
            f"""
            SELECT COUNT(*)
            FROM {TABLE_NAME}
            WHERE assignee = ? AND updated >= ?
        """,
            (assignee, seven_days_ago),
        )
        stats["last_7_days"] = cursor.fetchone()[0]

    return stats


def get_time_based_story_points_stats(cursor, assignee):
    """Get story points statistics for closed stories in specific time periods."""
    from datetime import datetime, timedelta

    stats = {"last_1_day": 0, "last_3_days": 0, "last_7_days": 0}

    # Check if required columns exist
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if (
        "customfield_10026" not in columns
        or "updated" not in columns
        or "status" not in columns
    ):
        return stats

    # Calculate date thresholds
    now = datetime.now()
    one_day_ago = (now - timedelta(days=1)).isoformat()
    three_days_ago = (now - timedelta(days=3)).isoformat()
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    # Common "closed" status indicators
    closed_statuses = ["Done", "Closed", "Resolved", "Complete", "Completed"]
    status_placeholders = ",".join(["?" for _ in closed_statuses])

    # Last 1 day - sum of story points for closed stories
    cursor.execute(
        f"""
        SELECT SUM(CAST(customfield_10026 AS REAL))
        FROM {TABLE_NAME}
        WHERE assignee = ?
        AND updated >= ?
        AND status IN ({status_placeholders})
        AND customfield_10026 IS NOT NULL
        AND customfield_10026 != ''
    """,
        (assignee, one_day_ago, *closed_statuses),
    )
    result = cursor.fetchone()[0]
    stats["last_1_day"] = round(result, 1) if result else 0

    # Last 3 days
    cursor.execute(
        f"""
        SELECT SUM(CAST(customfield_10026 AS REAL))
        FROM {TABLE_NAME}
        WHERE assignee = ?
        AND updated >= ?
        AND status IN ({status_placeholders})
        AND customfield_10026 IS NOT NULL
        AND customfield_10026 != ''
    """,
        (assignee, three_days_ago, *closed_statuses),
    )
    result = cursor.fetchone()[0]
    stats["last_3_days"] = round(result, 1) if result else 0

    # Last 7 days
    cursor.execute(
        f"""
        SELECT SUM(CAST(customfield_10026 AS REAL))
        FROM {TABLE_NAME}
        WHERE assignee = ?
        AND updated >= ?
        AND status IN ({status_placeholders})
        AND customfield_10026 IS NOT NULL
        AND customfield_10026 != ''
    """,
        (assignee, seven_days_ago, *closed_statuses),
    )
    result = cursor.fetchone()[0]
    stats["last_7_days"] = round(result, 1) if result else 0

    return stats


def get_unified_commit_stats(cursor, assignee):
    """Get total commit statistics for an assignee."""
    # Extract email from assignee JSON if possible
    try:
        import ast

        assignee_dict = ast.literal_eval(assignee)
        assignee_email = assignee_dict.get("emailAddress", "")
        assignee_name = assignee_dict.get("displayName", "")
    except:
        assignee_email = ""
        assignee_name = assignee

    # Get all commits for this assignee
    search_conditions = []
    search_params = []

    if assignee_email:
        search_conditions.append("author_email = ?")
        search_params.append(assignee_email)
    if assignee_name:
        search_conditions.append("author_name = ?")
        search_params.append(assignee_name)

    if not search_conditions:
        return 0

    # Use OR to combine conditions, but avoid double counting
    where_clause = " OR ".join(search_conditions)

    cursor.execute(
        f"""
        SELECT COUNT(DISTINCT hash)
        FROM git_commits
        WHERE {where_clause}
    """,
        search_params,
    )

    result = cursor.fetchone()
    return result[0] if result else 0


def get_unified_jira_stats(cursor, assignee):
    """Get total Jira update statistics for an assignee."""
    # Check if updated column exists
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if "updated" not in columns:
        return 0

    # Count all Jira updates for this assignee
    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM {TABLE_NAME}
        WHERE assignee = ?
    """,
        (assignee,),
    )

    result = cursor.fetchone()
    return result[0] if result else 0


def get_unified_story_points_stats(cursor, assignee):
    """Get total story points for closed stories for an assignee."""
    # Check if required columns exist
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if "customfield_10026" not in columns or "status" not in columns:
        return 0

    # Common "closed" status indicators
    closed_statuses = ["Done", "Closed", "Resolved", "Complete", "Completed"]
    status_placeholders = ",".join(["?" for _ in closed_statuses])

    # Sum of story points for closed stories
    cursor.execute(
        f"""
        SELECT SUM(CAST(customfield_10026 AS REAL))
        FROM {TABLE_NAME}
        WHERE assignee = ?
        AND status IN ({status_placeholders})
        AND customfield_10026 IS NOT NULL
        AND customfield_10026 != ''
    """,
        (assignee, *closed_statuses),
    )

    result = cursor.fetchone()[0]
    return round(result, 1) if result else 0


def get_issue_codes_for_assignee(cursor, assignee):
    """Get issue codes for a specific assignee from the watches field."""
    # Check if watches column exists
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if "watches" not in columns:
        return []

    # Get watches data for this assignee
    cursor.execute(
        f"""
        SELECT watches
        FROM {TABLE_NAME}
        WHERE assignee = ? AND watches IS NOT NULL AND watches != ''
    """,
        (assignee,),
    )
    watches_data = cursor.fetchall()

    issue_codes = []
    for (watches_json,) in watches_data:
        issue_code = extract_issue_code_from_watches(watches_json)
        if issue_code:
            issue_codes.append(issue_code)

    return issue_codes


def display_basic_stats_summary(developer_basic_stats):
    """Display a summary table of unified developer statistics."""
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Developer")
    table.add_column("Email")
    table.add_column("Total Commits")
    table.add_column("Total Jira Updates")
    table.add_column("Total Story Points Closed")

    for assignee_json, stats in developer_basic_stats.items():
        # Extract clean name and email for display
        name, email = extract_developer_info(assignee_json)

        table.add_row(
            name,
            email,
            str(stats["total_commits"]),
            str(stats["total_jira_updates"]),
            str(stats["total_story_points_closed"]),
        )

    console.print("\n[bold yellow]Unified Developer Statistics Summary:[/bold yellow]")
    console.print(table)


def display_existing_basic_stats():
    """Display existing basic developer statistics from the JSON file."""
    from ..config import BASIC_STATS

    if not os.path.exists(BASIC_STATS):
        console.print(
            f"[bold red]No basic statistics file found: {BASIC_STATS}[/bold red]"
        )
        input("Press Enter to return to the menu...")
        return

    try:
        with open(BASIC_STATS, "r") as f:
            stats_data = json.load(f)

        developer_stats = stats_data.get("developers", {})
        if not developer_stats:
            console.print(
                "[bold red]No developer statistics found in the file.[/bold red]"
            )
            input("Press Enter to return to the menu...")
            return

        # Display the summary table
        display_basic_stats_summary(developer_stats)

        # Show file info
        generated_at = stats_data.get("generated_at", "Unknown")
        console.print(
            f"\n[bold green]Basic statistics loaded from: {BASIC_STATS}[/bold green]"
        )
        console.print(f"[bold yellow]Generated at: {generated_at}[/bold yellow]")

        input("\nPress Enter to return to the menu...")

    except Exception as e:
        console.print(
            f"[bold red]Error reading basic statistics file: {str(e)}[/bold red]"
        )
        input("Press Enter to return to the menu...")


def generate_sprint_stats_json():
    """Generates a JSON file with sprint-based developer statistics combining issues, commits, and sprints data."""
    sprint_stats_file = "ux/web/data/team_sprint_stats.json"

    if not os.path.exists(DB_NAME):
        console.print(
            "[bold red]Database does not exist. Please update issues and commits first.[/bold red]"
        )
        input("Press Enter to return to the menu...")
        return None

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Check if all required tables exist
        required_tables = [TABLE_NAME, "git_commits", f"{TABLE_NAME}_sprints"]
        for table in required_tables:
            cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            )
            if not cursor.fetchone():
                console.print(
                    f"[bold red]Required table '{table}' not found. Please ensure all data is loaded.[/bold red]"
                )
                input("Press Enter to return to the menu...")
                return None

        # Get all sprints
        cursor.execute(
            f"SELECT id, name, state, startDate, endDate FROM {TABLE_NAME}_sprints ORDER BY startDate"
        )
        sprints = cursor.fetchall()

        if not sprints:
            console.print("[bold red]No sprints found in the database.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        # Get all assignees from Jira issues (excluding empty/null assignees)
        cursor.execute(
            f"""
            SELECT DISTINCT assignee
            FROM {TABLE_NAME}
            WHERE assignee IS NOT NULL AND assignee != '' AND assignee != 'null'
        """
        )
        assignees = [row[0] for row in cursor.fetchall()]

        # Filter to include only specified emails
        filtered_assignees = []
        for assignee in assignees:
            _, email = extract_developer_info(assignee)
            if should_include_email(email):
                filtered_assignees.append(assignee)

        if not filtered_assignees:
            console.print(
                "[bold red]No assignees found after filtering excluded emails.[/bold red]"
            )
            input("Press Enter to return to the menu...")
            return None

        sprint_analytics = {}

        for sprint_id, sprint_name, sprint_state, start_date, end_date in sprints:
            sprint_key = f"{sprint_id}_{sprint_name.replace(' ', '_')}"

            sprint_analytics[sprint_key] = {
                "sprint_info": {
                    "id": sprint_id,
                    "name": sprint_name,
                    "state": sprint_state,
                    "start_date": start_date,
                    "end_date": end_date,
                },
                "developers": {},
            }

            # Get stats for each developer in this sprint
            for assignee in filtered_assignees:
                name, email = extract_developer_info(assignee)

                # Get sprint-specific stats for this developer
                sprint_stats = get_sprint_stats_for_developer(
                    cursor, assignee, sprint_id, start_date, end_date
                )

                # Only include developers who have activity in this sprint
                if (
                    sprint_stats["commits_in_sprint"] > 0
                    or sprint_stats["issues_assigned_in_sprint"] > 0
                    or sprint_stats["issues_closed_in_sprint"] > 0
                ):

                    sprint_analytics[sprint_key]["developers"][name] = {
                        "name": name,
                        "email": email,
                        "commits_in_sprint": sprint_stats["commits_in_sprint"],
                        "issues_assigned_in_sprint": sprint_stats[
                            "issues_assigned_in_sprint"
                        ],
                        "issues_closed_in_sprint": sprint_stats[
                            "issues_closed_in_sprint"
                        ],
                        "story_points_closed_in_sprint": sprint_stats[
                            "story_points_closed_in_sprint"
                        ],
                    }

        # Create final JSON structure
        final_json = {
            "generated_at": datetime.now().isoformat(),
            "sprint_analytics": sprint_analytics,
        }

        # Backup existing file if it exists
        if os.path.exists(sprint_stats_file):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            stats_dir = os.path.dirname(sprint_stats_file)
            backup_filename = os.path.join(
                stats_dir, f"team_sprint_stats_backup_{timestamp}.json"
            )
            shutil.copy2(sprint_stats_file, backup_filename)
            console.print(
                f"[bold yellow]Existing sprint stats file backed up to: {backup_filename}[/bold yellow]"
            )

        # Ensure directory exists
        os.makedirs(os.path.dirname(sprint_stats_file), exist_ok=True)

        # Write to sprint stats JSON file
        with open(sprint_stats_file, "w") as f:
            json.dump(final_json, f, indent=2, default=str)

        # Display summary
        display_sprint_stats_summary(sprint_analytics)

        console.print(
            f"\n[bold green]Sprint statistics file created: {sprint_stats_file}[/bold green]"
        )

        input("\nPress Enter to return to the menu...")
        return sprint_stats_file


def get_sprint_stats_for_developer(cursor, assignee, sprint_id, start_date, end_date):
    """Get sprint-specific statistics for a developer."""
    from datetime import datetime
    import re

    stats = {
        "commits_in_sprint": 0,
        "issues_assigned_in_sprint": 0,
        "issues_closed_in_sprint": 0,
        "story_points_closed_in_sprint": 0,
    }

    # Extract developer info - handle JSON string format
    try:
        import json

        assignee_dict = json.loads(assignee)
        assignee_email = assignee_dict.get("emailAddress", "")
        assignee_name = assignee_dict.get("displayName", "")
    except (json.JSONDecodeError, TypeError):
        # Fallback to ast.literal_eval for older format
        try:
            import ast

            assignee_dict = ast.literal_eval(assignee)
            assignee_email = assignee_dict.get("emailAddress", "")
            assignee_name = assignee_dict.get("displayName", "")
        except:
            assignee_email = ""
            assignee_name = assignee

    # Parse sprint dates - handle different timezone formats
    try:
        if start_date:
            # Handle both 'Z' and '+00:00' timezone formats
            start_date_clean = start_date.replace("Z", "+00:00")
            sprint_start = datetime.fromisoformat(start_date_clean)
        else:
            sprint_start = None

        if end_date:
            end_date_clean = end_date.replace("Z", "+00:00")
            sprint_end = datetime.fromisoformat(end_date_clean)
        else:
            sprint_end = None
    except Exception as e:
        console.print(
            f"[bold yellow]Warning: Could not parse sprint dates for sprint {sprint_id}: {e}[/bold yellow]"
        )
        sprint_start = None
        sprint_end = None

    # 1. Get commits during sprint period with improved date matching
    if sprint_start and sprint_end and (assignee_email or assignee_name):
        search_conditions = []
        search_params = []

        if assignee_email:
            search_conditions.append("author_email LIKE ?")
            search_params.append(f"%{assignee_email}%")
        if assignee_name:
            search_conditions.append("author_name LIKE ?")
            search_params.append(f"%{assignee_name}%")

        where_clause = " OR ".join(search_conditions)

        # Convert sprint dates to date-only format for comparison
        sprint_start_date = sprint_start.date()  # Convert to date object (YYYY-MM-DD)
        sprint_end_date = sprint_end.date()  # Convert to date object (YYYY-MM-DD)

        # Get all commits with dates for this developer
        cursor.execute(
            f"""
            SELECT DISTINCT hash, date
            FROM git_commits
            WHERE ({where_clause}) AND date IS NOT NULL
        """,
            search_params,
        )

        commit_data = cursor.fetchall()
        commits_in_range = 0

        for hash_val, date_str in commit_data:
            try:
                # Parse git date format: "Fri Sep 19 15:06:43 2025 -0600"
                # Remove timezone info first
                date_clean = re.sub(r"\s+[+-]\d{4}$", "", date_str.strip())

                # Parse the git date format
                commit_datetime = None
                try:
                    # Git format: "Fri Sep 19 15:06:43 2025"
                    commit_datetime = datetime.strptime(
                        date_clean, "%a %b %d %H:%M:%S %Y"
                    )
                except ValueError:
                    # Try alternative formats if needed
                    try:
                        commit_datetime = datetime.strptime(
                            date_clean, "%Y-%m-%d %H:%M:%S"
                        )
                    except ValueError:
                        try:
                            commit_datetime = datetime.strptime(date_clean, "%Y-%m-%d")
                        except ValueError:
                            continue

                if commit_datetime:
                    # Convert commit datetime to date-only for comparison
                    commit_date = commit_datetime.date()

                    # Compare date-only values (no time component)
                    if sprint_start_date <= commit_date <= sprint_end_date:
                        commits_in_range += 1

            except Exception as e:
                # Skip commits with unparseable dates
                continue

        stats["commits_in_sprint"] = commits_in_range

    # 2. Get issues assigned to developer that are in this sprint
    cursor.execute(
        f"""
        SELECT COUNT(*)
        FROM {TABLE_NAME}
        WHERE assignee = ? AND customfield_10020 LIKE ?
    """,
        (assignee, f"%{sprint_id}%"),
    )

    stats["issues_assigned_in_sprint"] = cursor.fetchone()[0]

    # 3. Get issues closed during sprint period - Fix status JSON parsing
    closed_statuses = ["Done", "Closed", "Resolved", "Complete", "Completed"]

    if sprint_start and sprint_end:
        sprint_start_str = sprint_start.isoformat()
        sprint_end_str = sprint_end.isoformat()

        # Get all issues for this assignee in this sprint within date range
        cursor.execute(
            f"""
            SELECT status, customfield_10026
            FROM {TABLE_NAME}
            WHERE assignee = ?
            AND customfield_10020 LIKE ?
            AND updated >= ? AND updated <= ?
        """,
            (assignee, f"%{sprint_id}%", sprint_start_str, sprint_end_str),
        )

        issues_data = cursor.fetchall()
        closed_count = 0
        total_story_points = 0

        for status_json, story_points_str in issues_data:
            try:
                # Parse status JSON to get actual status name
                status_dict = json.loads(status_json)
                status_name = status_dict.get("name", "")

                if status_name in closed_statuses:
                    closed_count += 1

                    # Add story points if available
                    if (
                        story_points_str
                        and story_points_str.strip()
                        and story_points_str != "null"
                    ):
                        try:
                            story_points_value = float(story_points_str.strip())
                            total_story_points += story_points_value
                        except (ValueError, TypeError):
                            continue

            except (json.JSONDecodeError, TypeError):
                # Try fallback parsing for status
                try:
                    import ast

                    status_dict = ast.literal_eval(status_json)
                    status_name = status_dict.get("name", "")

                    if status_name in closed_statuses:
                        closed_count += 1

                        # Add story points if available
                        if (
                            story_points_str
                            and story_points_str.strip()
                            and story_points_str != "null"
                        ):
                            try:
                                story_points_value = float(story_points_str.strip())
                                total_story_points += story_points_value
                            except (ValueError, TypeError):
                                continue
                except:
                    continue

        stats["issues_closed_in_sprint"] = closed_count
        stats["story_points_closed_in_sprint"] = round(total_story_points, 1)
    else:
        # If no date range, just check for closed issues in the sprint
        cursor.execute(
            f"""
            SELECT status, customfield_10026
            FROM {TABLE_NAME}
            WHERE assignee = ?
            AND customfield_10020 LIKE ?
        """,
            (assignee, f"%{sprint_id}%"),
        )

        issues_data = cursor.fetchall()
        closed_count = 0
        total_story_points = 0

        for status_json, story_points_str in issues_data:
            try:
                # Parse status JSON to get actual status name
                status_dict = json.loads(status_json)
                status_name = status_dict.get("name", "")

                if status_name in closed_statuses:
                    closed_count += 1

                    # Add story points if available
                    if (
                        story_points_str
                        and story_points_str.strip()
                        and story_points_str != "null"
                    ):
                        try:
                            story_points_value = float(story_points_str.strip())
                            total_story_points += story_points_value
                        except (ValueError, TypeError):
                            continue

            except (json.JSONDecodeError, TypeError):
                # Try fallback parsing for status
                try:
                    import ast

                    status_dict = ast.literal_eval(status_json)
                    status_name = status_dict.get("name", "")

                    if status_name in closed_statuses:
                        closed_count += 1

                        # Add story points if available
                        if (
                            story_points_str
                            and story_points_str.strip()
                            and story_points_str != "null"
                        ):
                            try:
                                story_points_value = float(story_points_str.strip())
                                total_story_points += story_points_value
                            except (ValueError, TypeError):
                                continue
                except:
                    continue

        stats["issues_closed_in_sprint"] = closed_count
        stats["story_points_closed_in_sprint"] = round(total_story_points, 1)

    return stats


def display_sprint_stats_summary(sprint_analytics):
    """Display a summary table of sprint statistics."""
    console.print("\n[bold yellow]Sprint Analytics Summary:[/bold yellow]")

    for sprint_key, sprint_data in sprint_analytics.items():
        sprint_info = sprint_data["sprint_info"]
        developers = sprint_data["developers"]

        if not developers:
            continue

        console.print(
            f"\n[bold cyan]Sprint: {sprint_info['name']} ({sprint_info['state']})[/bold cyan]"
        )

        table = Table(show_header=True, header_style="bold green")
        table.add_column("Developer")
        table.add_column("Commits")
        table.add_column("Issues Assigned")
        table.add_column("Issues Closed")
        table.add_column("Story Points Closed")

        for dev_name, dev_stats in developers.items():
            table.add_row(
                dev_stats["name"],
                str(dev_stats["commits_in_sprint"]),
                str(dev_stats["issues_assigned_in_sprint"]),
                str(dev_stats["issues_closed_in_sprint"]),
                str(dev_stats["story_points_closed_in_sprint"]),
            )

        console.print(table)


def display_existing_sprint_stats():
    """Display existing sprint statistics from the JSON file."""
    sprint_stats_file = "ux/web/data/team_sprint_stats.json"

    if not os.path.exists(sprint_stats_file):
        console.print(
            f"[bold red]No sprint statistics file found: {sprint_stats_file}[/bold red]"
        )
        input("Press Enter to return to the menu...")
        return

    try:
        with open(sprint_stats_file, "r") as f:
            stats_data = json.load(f)

        sprint_analytics = stats_data.get("sprint_analytics", {})
        if not sprint_analytics:
            console.print("[bold red]No sprint analytics found in the file.[/bold red]")
            input("Press Enter to return to the menu...")
            return

        # Display the sprint analytics
        display_sprint_stats_summary(sprint_analytics)

        # Show file info
        generated_at = stats_data.get("generated_at", "Unknown")
        console.print(
            f"\n[bold green]Sprint statistics loaded from: {sprint_stats_file}[/bold green]"
        )
        console.print(f"[bold yellow]Generated at: {generated_at}[/bold yellow]")

        input("\nPress Enter to return to the menu...")

    except Exception as e:
        console.print(
            f"[bold red]Error reading sprint statistics file: {str(e)}[/bold red]"
        )
        input("Press Enter to return to the menu...")


# ============================================================================
# DEVELOPER ACTIVITY TRACKING (NEW)
# ============================================================================


def get_last_3_days_activity(cursor):
    """
    Get developer activity for last 3 days.
    Returns dict with developers array and summary.
    """
    from datetime import datetime, timedelta
    import re

    # Calculate cutoff date (3 days ago)
    cutoff_date = datetime.now() - timedelta(days=3)
    cutoff_str = cutoff_date.isoformat()

    # Get valid team members (assignees from Jira, filtered to include only specified emails)
    cursor.execute(
        f"""
        SELECT DISTINCT assignee
        FROM {TABLE_NAME}
        WHERE assignee IS NOT NULL AND assignee != '' AND assignee != 'null'
    """
    )
    assignees = [row[0] for row in cursor.fetchall()]

    # Filter to include only specified emails and build valid email set
    valid_emails = set()
    valid_assignees = {}
    for assignee in assignees:
        name, email = extract_developer_info(assignee)
        if should_include_email(email):
            valid_emails.add(email.lower())
            valid_assignees[email.lower()] = (name, email)

    # Dictionary to accumulate activity per developer
    developer_activity = defaultdict(
        lambda: {
            "email": "",
            "name": "",
            "jira_actions": 0,
            "repo_actions": 0,
            "breakdown": {
                "issues_created": 0,
                "issues_updated": 0,
                "status_changes": 0,
                "commits": 0,
            },
        }
    )

    # 1. JIRA ACTIVITY

    # Issues created in last 3 days
    cursor.execute(
        f"""
        SELECT creator FROM {TABLE_NAME}
        WHERE created >= ?
    """,
        (cutoff_str,),
    )
    for (creator_json,) in cursor.fetchall():
        if creator_json:
            name, email = extract_developer_info(creator_json)
            # Only count if this person is a valid team member
            if email.lower() in valid_emails:
                developer_activity[email]["email"] = email
                developer_activity[email]["name"] = name
                developer_activity[email]["breakdown"]["issues_created"] += 1
                developer_activity[email]["jira_actions"] += 1

    # Issues updated in last 3 days (attribute to assignee)
    cursor.execute(
        f"""
        SELECT assignee FROM {TABLE_NAME}
        WHERE updated >= ? AND assignee IS NOT NULL AND assignee != ''
    """,
        (cutoff_str,),
    )
    for (assignee_json,) in cursor.fetchall():
        if assignee_json:
            name, email = extract_developer_info(assignee_json)
            # Only count if this person is a valid team member
            if email.lower() in valid_emails:
                developer_activity[email]["email"] = email
                developer_activity[email]["name"] = name
                developer_activity[email]["breakdown"]["issues_updated"] += 1
                developer_activity[email]["jira_actions"] += 1

    # Status changes in last 3 days (attribute to assignee)
    cursor.execute(
        f"""
        SELECT assignee FROM {TABLE_NAME}
        WHERE statuscategorychangedate >= ? AND assignee IS NOT NULL AND assignee != ''
    """,
        (cutoff_str,),
    )
    for (assignee_json,) in cursor.fetchall():
        if assignee_json:
            name, email = extract_developer_info(assignee_json)
            # Only count if this person is a valid team member
            if email.lower() in valid_emails:
                developer_activity[email]["email"] = email
                developer_activity[email]["name"] = name
                developer_activity[email]["breakdown"]["status_changes"] += 1
                developer_activity[email]["jira_actions"] += 1

    # 2. REPO ACTIVITY

    # Commits in last 3 days
    cursor.execute(
        """
        SELECT author_name, author_email, date
        FROM git_commits
        WHERE date IS NOT NULL
    """
    )

    for author_name, author_email, date_str in cursor.fetchall():
        try:
            # Parse git date and check if within last 3 days
            date_clean = re.sub(r"\s+[+-]\d{4}$", "", date_str.strip())
            commit_date = datetime.strptime(date_clean, "%a %b %d %H:%M:%S %Y")

            if commit_date >= cutoff_date:
                # Match to Jira user by email - only count if valid team member
                if author_email and author_email.lower() in valid_emails:
                    # Use the name from Jira assignee data for consistency
                    jira_name, jira_email = valid_assignees[author_email.lower()]
                    developer_activity[jira_email]["email"] = jira_email
                    developer_activity[jira_email]["name"] = jira_name
                    developer_activity[jira_email]["breakdown"]["commits"] += 1
                    developer_activity[jira_email]["repo_actions"] += 1
        except:
            continue

    # 3. Calculate totals and convert to array
    developers = []
    for email, data in developer_activity.items():
        if data["email"]:  # Only include if we have email
            data["total_activity"] = data["jira_actions"] + data["repo_actions"]
            developers.append(data)

    # 4. Sort by total_activity (desc), then repo_actions (desc)
    developers.sort(
        key=lambda x: (x["total_activity"], x["repo_actions"]), reverse=True
    )

    # 5. Calculate summary
    summary = {
        "total_jira_actions": sum(d["jira_actions"] for d in developers),
        "total_repo_actions": sum(d["repo_actions"] for d in developers),
        "total_activity": sum(d["total_activity"] for d in developers),
        "active_developers": len(developers),
        "most_active_developer": developers[0]["name"] if developers else "None",
    }

    return {
        "period": {"start": cutoff_date.isoformat(), "end": datetime.now().isoformat()},
        "developers": developers,
        "summary": summary,
    }


def get_sprint_activity(
    cursor, sprint_id, sprint_name, start_date, end_date, sprint_state
):
    """
    Get developer activity for a specific sprint.
    Returns dict with developers array and summary.
    """
    from datetime import datetime
    import re

    # Parse sprint dates
    try:
        sprint_start = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        sprint_end = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except:
        return None

    # Get valid team members (assignees from Jira, filtered to include only specified emails)
    cursor.execute(
        f"""
        SELECT DISTINCT assignee
        FROM {TABLE_NAME}
        WHERE assignee IS NOT NULL AND assignee != '' AND assignee != 'null'
    """
    )
    assignees = [row[0] for row in cursor.fetchall()]

    # Filter to include only specified emails and build valid email set
    valid_emails = set()
    valid_assignees = {}
    for assignee in assignees:
        name, email = extract_developer_info(assignee)
        if should_include_email(email):
            valid_emails.add(email.lower())
            valid_assignees[email.lower()] = (name, email)

    # Dictionary to accumulate activity per developer
    developer_activity = defaultdict(
        lambda: {
            "email": "",
            "name": "",
            "jira_actions": 0,
            "repo_actions": 0,
            "breakdown": {
                "issues_created": 0,
                "issues_assigned": 0,
                "issues_updated": 0,
                "status_changes": 0,
                "commits": 0,
            },
        }
    )

    # 1. JIRA ACTIVITY

    # Issues created in sprint period
    cursor.execute(
        f"""
        SELECT creator, created FROM {TABLE_NAME}
        WHERE created >= ? AND created <= ? AND creator IS NOT NULL AND creator != ''
    """,
        (start_date, end_date),
    )
    for creator_json, created in cursor.fetchall():
        if creator_json:
            name, email = extract_developer_info(creator_json)
            # Only count if this person is a valid team member
            if email.lower() in valid_emails:
                developer_activity[email]["email"] = email
                developer_activity[email]["name"] = name
                developer_activity[email]["breakdown"]["issues_created"] += 1
                developer_activity[email]["jira_actions"] += 1

    # Issues assigned to this sprint
    cursor.execute(
        f"""
        SELECT assignee, customfield_10020 FROM {TABLE_NAME}
        WHERE customfield_10020 LIKE ? AND assignee IS NOT NULL AND assignee != ''
    """,
        (f"%{sprint_id}%",),
    )
    for assignee_json, sprints_json in cursor.fetchall():
        if assignee_json:
            name, email = extract_developer_info(assignee_json)
            # Only count if this person is a valid team member
            if email.lower() in valid_emails:
                developer_activity[email]["email"] = email
                developer_activity[email]["name"] = name
                developer_activity[email]["breakdown"]["issues_assigned"] += 1
                developer_activity[email]["jira_actions"] += 1

    # Issues updated in sprint period (attribute to assignee)
    cursor.execute(
        f"""
        SELECT assignee, updated FROM {TABLE_NAME}
        WHERE updated >= ? AND updated <= ? AND assignee IS NOT NULL AND assignee != ''
    """,
        (start_date, end_date),
    )
    for assignee_json, updated in cursor.fetchall():
        if assignee_json:
            name, email = extract_developer_info(assignee_json)
            # Only count if this person is a valid team member
            if email.lower() in valid_emails:
                developer_activity[email]["email"] = email
                developer_activity[email]["name"] = name
                developer_activity[email]["breakdown"]["issues_updated"] += 1
                developer_activity[email]["jira_actions"] += 1

    # Status changes in sprint period (attribute to assignee)
    cursor.execute(
        f"""
        SELECT assignee, statuscategorychangedate FROM {TABLE_NAME}
        WHERE statuscategorychangedate >= ? AND statuscategorychangedate <= ?
        AND assignee IS NOT NULL AND assignee != ''
    """,
        (start_date, end_date),
    )
    for assignee_json, status_date in cursor.fetchall():
        if assignee_json:
            name, email = extract_developer_info(assignee_json)
            # Only count if this person is a valid team member
            if email.lower() in valid_emails:
                developer_activity[email]["email"] = email
                developer_activity[email]["name"] = name
                developer_activity[email]["breakdown"]["status_changes"] += 1
                developer_activity[email]["jira_actions"] += 1

    # 2. REPO ACTIVITY

    # Commits in sprint period
    cursor.execute(
        """
        SELECT author_name, author_email, date
        FROM git_commits
        WHERE date IS NOT NULL
    """
    )

    sprint_start_date = sprint_start.date()
    sprint_end_date = sprint_end.date()

    for author_name, author_email, date_str in cursor.fetchall():
        try:
            date_clean = re.sub(r"\s+[+-]\d{4}$", "", date_str.strip())
            commit_date = datetime.strptime(date_clean, "%a %b %d %H:%M:%S %Y")
            commit_date_only = commit_date.date()

            if sprint_start_date <= commit_date_only <= sprint_end_date:
                # Match to Jira user by email - only count if valid team member
                if author_email and author_email.lower() in valid_emails:
                    # Use the name from Jira assignee data for consistency
                    jira_name, jira_email = valid_assignees[author_email.lower()]
                    developer_activity[jira_email]["email"] = jira_email
                    developer_activity[jira_email]["name"] = jira_name
                    developer_activity[jira_email]["breakdown"]["commits"] += 1
                    developer_activity[jira_email]["repo_actions"] += 1
        except:
            continue

    # 3. Calculate totals and convert to array
    developers = []
    for email, data in developer_activity.items():
        if data["email"]:
            data["total_activity"] = data["jira_actions"] + data["repo_actions"]
            developers.append(data)

    # 4. Sort by total_activity (desc), then repo_actions (desc)
    developers.sort(
        key=lambda x: (x["total_activity"], x["repo_actions"]), reverse=True
    )

    # 5. Calculate summary
    summary = {
        "total_developers": len(developers),
        "total_jira_actions": sum(d["jira_actions"] for d in developers),
        "total_repo_actions": sum(d["repo_actions"] for d in developers),
        "total_activity": sum(d["total_activity"] for d in developers),
        "avg_activity_per_developer": (
            round(sum(d["total_activity"] for d in developers) / len(developers), 2)
            if developers
            else 0
        ),
        "most_active_developer": developers[0]["email"] if developers else None,
    }

    return {
        "sprint_id": sprint_id,
        "sprint_name": sprint_name,
        "sprint_state": sprint_state,
        "start_date": start_date,
        "end_date": end_date,
        "developers": developers,
        "summary": summary,
    }


def calculate_developer_summary(cursor, sprint_activity_list):
    """
    Calculate all-time developer summary across all sprints.
    Returns array of developer summaries sorted by total activity.
    """
    # Aggregate activity per developer across all sprints
    developer_totals = defaultdict(
        lambda: {
            "email": "",
            "name": "",
            "total_activity_all_sprints": 0,
            "total_jira_actions": 0,
            "total_repo_actions": 0,
            "sprints_participated": 0,
            "sprint_breakdown": [],
        }
    )

    # Accumulate from sprint data
    for sprint in sprint_activity_list:
        for dev in sprint["developers"]:
            email = dev["email"]
            developer_totals[email]["email"] = email
            developer_totals[email]["name"] = dev["name"]
            developer_totals[email]["total_activity_all_sprints"] += dev[
                "total_activity"
            ]
            developer_totals[email]["total_jira_actions"] += dev["jira_actions"]
            developer_totals[email]["total_repo_actions"] += dev["repo_actions"]
            developer_totals[email]["sprints_participated"] += 1
            developer_totals[email]["sprint_breakdown"].append(
                {
                    "sprint_name": sprint["sprint_name"],
                    "activity": dev["total_activity"],
                }
            )

    # Get last 3 days activity for each developer
    last_3_days = get_last_3_days_activity(cursor)
    last_3_days_map = {
        dev["email"]: dev["total_activity"] for dev in last_3_days["developers"]
    }

    # Convert to array and calculate averages
    developer_summary = []
    for email, data in developer_totals.items():
        if data["email"]:
            # Calculate average activity per sprint
            avg_activity = (
                round(
                    data["total_activity_all_sprints"] / data["sprints_participated"], 2
                )
                if data["sprints_participated"] > 0
                else 0
            )

            # Add fields that match what the HTML dashboard expects
            data["avg_activity_per_sprint"] = avg_activity
            data["last_3_days_activity"] = last_3_days_map.get(email, 0)
            # Add aliases for consistency with sprint_activity format
            data["total_activity"] = data["total_activity_all_sprints"]
            data["jira_actions"] = data["total_jira_actions"]
            data["repo_actions"] = data["total_repo_actions"]

            developer_summary.append(data)

    # Sort by total_activity (desc), then repo_actions (desc)
    developer_summary.sort(
        key=lambda x: (x["total_activity"], x["repo_actions"]), reverse=True
    )

    return developer_summary


def generate_developer_activity_json():
    """
    Generate comprehensive developer activity JSON file.
    Includes last 3 days activity and sprint-by-sprint breakdown.
    """
    from datetime import datetime
    import shutil

    output_file = "ux/web/data/developer_activity.json"

    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database does not exist.[/bold red]")
        input("Press Enter to return to the menu...")
        return None

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Check if required tables exist
        required_tables = [TABLE_NAME, "git_commits", f"{TABLE_NAME}_sprints"]
        for table in required_tables:
            cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'"
            )
            if not cursor.fetchone():
                console.print(
                    f"[bold red]Required table '{table}' not found.[/bold red]"
                )
                input("Press Enter to return to the menu...")
                return None

        # 1. Get last 3 days activity
        console.print("[yellow]Calculating last 3 days activity...[/yellow]")
        last_3_days = get_last_3_days_activity(cursor)

        # 2. Get all sprints
        cursor.execute(
            f"""
            SELECT id, name, state, startDate, endDate 
            FROM {TABLE_NAME}_sprints 
            ORDER BY startDate DESC
        """
        )
        sprints = cursor.fetchall()

        if not sprints:
            console.print("[bold red]No sprints found in database.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        # 3. Get activity for each sprint
        console.print("[yellow]Calculating sprint activity...[/yellow]")
        sprint_activity = []
        for sprint_id, name, state, start, end in sprints:
            activity = get_sprint_activity(cursor, sprint_id, name, start, end, state)
            if activity:
                sprint_activity.append(activity)

        # 4. Calculate developer summary (all-time)
        console.print("[yellow]Calculating developer summaries...[/yellow]")
        developer_summary = calculate_developer_summary(cursor, sprint_activity)

        # 5. Calculate activity trends
        activity_trends = {
            "by_sprint": [
                {
                    "sprint_name": s["sprint_name"],
                    "total_activity": s["summary"]["total_activity"],
                    "jira_actions": s["summary"]["total_jira_actions"],
                    "repo_actions": s["summary"]["total_repo_actions"],
                }
                for s in sprint_activity
            ],
            "top_performers_last_3_days": last_3_days["developers"][:5],
            "top_performers_current_sprint": (
                sprint_activity[0]["developers"][:5] if sprint_activity else []
            ),
        }

        # 6. Build final JSON structure
        final_json = {
            "generated_at": datetime.now().isoformat(),
            "metadata": {
                "total_developers": len(developer_summary),
                "total_sprints": len(sprint_activity),
                "active_sprint": (
                    sprint_activity[0]["sprint_name"] if sprint_activity else None
                ),
                "data_period": {
                    "earliest": sprints[-1][3] if sprints else None,
                    "latest": datetime.now().isoformat(),
                },
            },
            "last_3_days_activity": last_3_days,
            "sprint_activity": sprint_activity,
            "developer_summary": developer_summary,
            "activity_trends": activity_trends,
        }

        # 7. Backup existing file
        if os.path.exists(output_file):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"ux/web/data/developer_activity_backup_{timestamp}.json"
            shutil.copy2(output_file, backup_file)
            console.print(f"[yellow]Backed up to: {backup_file}[/yellow]")

        # 8. Write JSON file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            json.dump(final_json, f, indent=2, default=str)

        # 9. Display summary
        display_developer_activity_summary(last_3_days, sprint_activity)

        console.print(
            f"\n[bold green]Developer activity JSON created: {output_file}[/bold green]"
        )
        input("\nPress Enter to return to the menu...")
        return output_file


def display_developer_activity_summary(last_3_days, sprint_activity):
    """Display summary of developer activity."""

    # Last 3 days summary
    console.print(
        "\n[bold yellow]Last 3 Days Activity - Top 10 Developers:[/bold yellow]"
    )
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Rank")
    table.add_column("Developer")
    table.add_column("Email")
    table.add_column("Total Activity")
    table.add_column("Jira Actions")
    table.add_column("Repo Actions")

    for idx, dev in enumerate(last_3_days["developers"][:10], 1):
        table.add_row(
            str(idx),
            dev["name"],
            dev["email"],
            str(dev["total_activity"]),
            str(dev["jira_actions"]),
            str(dev["repo_actions"]),
        )

    console.print(table)

    # Current sprint summary
    if sprint_activity:
        current_sprint = sprint_activity[0]
        console.print(
            f"\n[bold yellow]Current Sprint: {current_sprint['sprint_name']} - Top 10 Developers:[/bold yellow]"
        )

        table2 = Table(show_header=True, header_style="bold green")
        table2.add_column("Rank")
        table2.add_column("Developer")
        table2.add_column("Email")
        table2.add_column("Total Activity")
        table2.add_column("Jira Actions")
        table2.add_column("Repo Actions")

        for idx, dev in enumerate(current_sprint["developers"][:10], 1):
            table2.add_row(
                str(idx),
                dev["name"],
                dev["email"],
                str(dev["total_activity"]),
                str(dev["jira_actions"]),
                str(dev["repo_actions"]),
            )

        console.print(table2)

        # Sprint summary stats
        summary = current_sprint["summary"]
        console.print(f"\n[bold cyan]Sprint Summary:[/bold cyan]")
        console.print(f"  Total Developers: {summary['total_developers']}")
        console.print(f"  Total Activity: {summary['total_activity']}")
        console.print(f"  Total Jira Actions: {summary['total_jira_actions']}")
        console.print(f"  Total Repo Actions: {summary['total_repo_actions']}")
        console.print(
            f"  Avg Activity per Developer: {summary['avg_activity_per_developer']}"
        )


# ============================================================================
# Daily Activity Report Functions
# ============================================================================

def get_daily_activity_by_buckets(target_date=None, tz=None):
    """Get developer activity by time buckets for a specific date.
    
    Time buckets:
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
                        "10am-12pm": {"jira": 0, "repo": 0, "total": 0},
                        "12pm-2pm": {"jira": 0, "repo": 0, "total": 0},
                        "2pm-4pm": {"jira": 0, "repo": 0, "total": 0},
                        "4pm-6pm": {"jira": 0, "repo": 0, "total": 0},
                    },
                    "off_hours": {"jira": 0, "repo": 0, "total": 0},
                    "daily_total": {"jira": 0, "repo": 0, "total": 0}
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
            
            for author_email, author_name, commit_date_str in commits:
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
    
    console.print(f"[bold green]Daily activity collection complete![/bold green]")
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
        console.print(f"[bold red]Error: Cannot generate report for future date {target_date}[/bold red]")
        console.print(f"[bold yellow]Today is {today}. Please select today or an earlier date.[/bold yellow]")
        return None
    
    console.print(f"\n[bold cyan]Generating Daily Activity Report for {target_date}[/bold cyan]")
    
    # Collect activity data
    daily_activity = get_daily_activity_by_buckets(target_date, tz)
    
    if not daily_activity:
        console.print("[bold red]No activity data collected. Aborting report generation.[/bold red]")
        return None
    
    # Convert to list format for JSON
    developers_list = []
    for email, data in daily_activity.items():
        developers_list.append(data)
    
    # Sort by total activity (descending)
    developers_list.sort(key=lambda d: d['daily_total']['total'], reverse=True)
    
    # Calculate summary statistics
    total_developers = len(developers_list)
    total_activity = sum(d['daily_total']['total'] for d in developers_list)
    total_jira = sum(d['daily_total']['jira'] for d in developers_list)
    total_repo = sum(d['daily_total']['repo'] for d in developers_list)
    
    # Find most active bucket
    bucket_totals = {}
    for bucket in get_all_time_buckets():
        if bucket == "off_hours":
            bucket_totals[bucket] = sum(d['off_hours']['total'] for d in developers_list)
        else:
            bucket_totals[bucket] = sum(d['buckets'][bucket]['total'] for d in developers_list)
    
    most_active_bucket = max(bucket_totals.items(), key=lambda x: x[1])[0] if bucket_totals else "N/A"
    
    # Calculate off-hours percentage
    off_hours_total = bucket_totals.get('off_hours', 0)
    off_hours_percentage = round((off_hours_total / total_activity * 100), 1) if total_activity > 0 else 0
    
    # Build JSON structure
    report_data = {
        "generated_at": datetime.now(tz).isoformat(),
        "metadata": {
            "report_date": str(target_date),
            "timezone": str(tz),
            "time_buckets": ["10am-12pm", "12pm-2pm", "2pm-4pm", "4pm-6pm"],
            "off_hours_window": "6pm previous day to 8am current day"
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
            "bucket_totals": bucket_totals
        }
    }
    
    # Backup existing file
    backup_daily_report_file(output_file)
    
    # Write JSON file
    try:
        with open(output_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        console.print(f"\n[bold green]Daily report generated successfully![/bold green]")
        console.print(f"[bold green]Output: {output_file}[/bold green]")
        
        # Display summary
        console.print(f"\n[bold cyan]Report Summary:[/bold cyan]")
        console.print(f"  Date: {target_date}")
        console.print(f"  Timezone: {tz}")
        console.print(f"  Total Developers: {total_developers}")
        console.print(f"  Total Activity: {total_activity}")
        console.print(f"  - Jira Actions: {total_jira}")
        console.print(f"  - Repo Actions: {total_repo}")
        console.print(f"  Most Active Bucket: {most_active_bucket} ({bucket_totals.get(most_active_bucket, 0)} actions)")
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
            console.print("[bold yellow]Generate it first using option 5.[/bold yellow]")
            return
        
        try:
            with open(json_file, 'r') as f:
                report_data = json.load(f)
            
            # Extract data from JSON structure
            metadata = report_data.get('metadata', {})
            developers_list = report_data.get('developers', [])
            summary = report_data.get('summary', {})
            
        except Exception as e:
            console.print(f"[bold red]Error loading JSON file: {e}[/bold red]")
            return
    else:
        # Convert dict to list format
        developers_list = list(daily_activity_data.values())
        developers_list.sort(key=lambda d: d['daily_total']['total'], reverse=True)
        metadata = None
        summary = None
    
    if not developers_list:
        console.print("[bold yellow]No developer activity data to display.[/bold yellow]")
        return
    
    # Display header
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]")
    console.print("[bold cyan]                    DAILY ACTIVITY REPORT                              [/bold cyan]")
    console.print("[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]")
    
    if metadata:
        console.print(f"\n[bold yellow]Report Date:[/bold yellow] {metadata.get('report_date', 'N/A')}")
        console.print(f"[bold yellow]Timezone:[/bold yellow] {metadata.get('timezone', 'N/A')}")
        console.print(f"[bold yellow]Generated:[/bold yellow] {report_data.get('generated_at', 'N/A')}\n")
    
    # Create Rich table
    table = Table(show_header=True, header_style="bold cyan", title="Activity by Time Bucket", 
                  title_style="bold magenta", border_style="cyan")
    
    # Add columns
    table.add_column("Developer", style="bold white", width=25)
    table.add_column("10am", justify="center", width=12)
    table.add_column("12pm", justify="center", width=12)
    table.add_column("2pm", justify="center", width=12)
    table.add_column("4pm", justify="center", width=12)
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
        "10am-12pm": 0,
        "12pm-2pm": 0,
        "2pm-4pm": 0,
        "4pm-6pm": 0,
        "off_hours": 0
    }
    
    displayed_count = 0
    max_display = 15
    
    for dev in developers_list:
        if dev['daily_total']['total'] == 0:
            continue  # Skip developers with no activity
        
        if displayed_count >= max_display:
            break
        
        name = dev['name'][:24]  # Truncate long names
        
        # Format each bucket
        bucket_10_12 = format_cell(
            dev['buckets']['10am-12pm']['total'],
            dev['buckets']['10am-12pm']['jira'],
            dev['buckets']['10am-12pm']['repo']
        )
        bucket_12_2 = format_cell(
            dev['buckets']['12pm-2pm']['total'],
            dev['buckets']['12pm-2pm']['jira'],
            dev['buckets']['12pm-2pm']['repo']
        )
        bucket_2_4 = format_cell(
            dev['buckets']['2pm-4pm']['total'],
            dev['buckets']['2pm-4pm']['jira'],
            dev['buckets']['2pm-4pm']['repo']
        )
        bucket_4_6 = format_cell(
            dev['buckets']['4pm-6pm']['total'],
            dev['buckets']['4pm-6pm']['jira'],
            dev['buckets']['4pm-6pm']['repo']
        )
        off_hours = format_cell(
            dev['off_hours']['total'],
            dev['off_hours']['jira'],
            dev['off_hours']['repo']
        )
        
        total = f"[bold]{dev['daily_total']['total']}[/bold]"
        
        table.add_row(name, bucket_10_12, bucket_12_2, bucket_2_4, bucket_4_6, off_hours, total)
        
        # Accumulate totals
        total_jira += dev['daily_total']['jira']
        total_repo += dev['daily_total']['repo']
        total_activity += dev['daily_total']['total']
        
        bucket_totals["10am-12pm"] += dev['buckets']['10am-12pm']['total']
        bucket_totals["12pm-2pm"] += dev['buckets']['12pm-2pm']['total']
        bucket_totals["2pm-4pm"] += dev['buckets']['2pm-4pm']['total']
        bucket_totals["4pm-6pm"] += dev['buckets']['4pm-6pm']['total']
        bucket_totals["off_hours"] += dev['off_hours']['total']
        
        displayed_count += 1
    
    # Add separator
    table.add_row("─" * 24, "─" * 10, "─" * 10, "─" * 10, "─" * 10, "─" * 10, "─" * 8, style="dim")
    
    # Add totals row
    table.add_row(
        f"[bold cyan]TOTALS ({displayed_count} devs)[/bold cyan]",
        f"[bold]{bucket_totals['10am-12pm']}[/bold]",
        f"[bold]{bucket_totals['12pm-2pm']}[/bold]",
        f"[bold]{bucket_totals['2pm-4pm']}[/bold]",
        f"[bold]{bucket_totals['4pm-6pm']}[/bold]",
        f"[bold yellow]{bucket_totals['off_hours']}[/bold yellow]",
        f"[bold green]{total_activity}[/bold green]"
    )
    
    # Display table
    console.print(table)
    
    # Display legend
    console.print("\n[bold]Legend:[/bold] [dim](J=Jira, R=Repo)[/dim]")
    console.print("[bold green]■[/bold green] High (10+)  [green]■[/green] Medium (5-9)  [yellow]■[/yellow] Low (3-4)  [white]■[/white] Minimal (1-2)")
    
    # Display summary statistics
    if summary:
        console.print("\n[bold cyan]Summary Statistics:[/bold cyan]")
        console.print(f"  Total Developers: {summary.get('total_developers', 'N/A')}")
        console.print(f"  Total Activity: {summary.get('total_activity', total_activity)}")
        console.print(f"  - Jira Actions: {summary.get('total_jira_actions', total_jira)}")
        console.print(f"  - Repo Actions: {summary.get('total_repo_actions', total_repo)}")
        console.print(f"  Most Active Bucket: [bold]{summary.get('most_active_bucket', 'N/A')}[/bold]")
        console.print(f"  Off-Hours Activity: {summary.get('off_hours_activity', 0)} ({summary.get('off_hours_percentage', 0)}%)")
    else:
        console.print("\n[bold cyan]Summary Statistics:[/bold cyan]")
        console.print(f"  Displayed Developers: {displayed_count}")
        console.print(f"  Total Activity: {total_activity}")
        console.print(f"  - Jira Actions: {total_jira}")
        console.print(f"  - Repo Actions: {total_repo}")
    
    if displayed_count < len(developers_list):
        remaining = len(developers_list) - displayed_count
        console.print(f"\n[dim]Note: {remaining} developers with no activity not shown[/dim]")
    
    console.print("\n[bold cyan]═══════════════════════════════════════════════════════════════════════[/bold cyan]\n")
