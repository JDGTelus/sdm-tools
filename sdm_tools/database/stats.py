"""Statistics generation functionality."""
import os
import sqlite3
import json
import shutil
from datetime import datetime
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from ..config import DB_NAME, TABLE_NAME, STATS_FILENAME, EXCLUDED_EMAILS

console = Console()


def backup_existing_stats_file():
    """Backup existing stats file if it exists."""
    if os.path.exists(STATS_FILENAME):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"team_simple_stats_backup_{timestamp}.json"
        shutil.copy2(STATS_FILENAME, backup_filename)
        console.print(
            f"[bold yellow]Existing stats file backed up to: {backup_filename}[/bold yellow]")
        return backup_filename
    return None


def extract_developer_info(assignee_json_str):
    """Extract name and email from the assignee JSON string."""
    try:
        import ast
        assignee_dict = ast.literal_eval(assignee_json_str)
        name = assignee_dict.get('displayName', 'Unknown')
        email = assignee_dict.get('emailAddress', 'Unknown')
        return name, email
    except:
        return assignee_json_str, 'Unknown'


def should_exclude_email(email):
    """Check if an email should be excluded from the output."""
    if not email or email == 'Unknown':
        return False

    # Clean up the excluded emails list (remove empty strings and whitespace)
    excluded_emails = [e.strip().lower() for e in EXCLUDED_EMAILS if e.strip()]

    # Check if the email matches any excluded email (case-insensitive)
    return email.lower() in excluded_emails


def generate_developer_stats_json():
    """Generates a JSON file with developer statistics from both Jira issues and git commits."""
    if not os.path.exists(DB_NAME):
        console.print(
            "[bold red]Database does not exist. Please update issues and commits first.[/bold red]")
        input("Press Enter to return to the menu...")
        return None

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Check if both tables exist
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
        if not cursor.fetchone():
            console.print(
                "[bold red]No Jira issues data found. Please update issues first.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'")
        if not cursor.fetchone():
            console.print(
                "[bold red]No git commits data found. Please update commits first.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        # Get all assignees from Jira issues (excluding empty/null assignees)
        cursor.execute(f"""
            SELECT DISTINCT assignee 
            FROM {TABLE_NAME} 
            WHERE assignee IS NOT NULL AND assignee != '' AND assignee != 'null'
        """)
        assignees = [row[0] for row in cursor.fetchall()]

        if not assignees:
            console.print(
                "[bold red]No assignees found in Jira issues.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        # Filter out excluded emails
        filtered_assignees = []
        for assignee in assignees:
            _, email = extract_developer_info(assignee)
            if not should_exclude_email(email):
                filtered_assignees.append(assignee)

        if not filtered_assignees:
            console.print(
                "[bold red]No assignees found after filtering excluded emails.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        developer_stats = {}

        for assignee in filtered_assignees:
            stats = {
                "name": assignee,
                "jira_stats": {},
                "git_stats": {},
                "combined_stats": {}
            }

            # Get Jira statistics for this assignee
            jira_stats = get_jira_stats_for_assignee(cursor, assignee)
            stats["jira_stats"] = jira_stats

            # Get Git statistics for this assignee (try to match by email or name)
            git_stats = get_git_stats_for_assignee(cursor, assignee)
            stats["git_stats"] = git_stats

            # Calculate combined statistics
            combined_stats = calculate_combined_stats(jira_stats, git_stats)
            stats["combined_stats"] = combined_stats

            developer_stats[assignee] = stats

        # Generate summary statistics
        summary_stats = generate_summary_stats(developer_stats)

        # Create final JSON structure
        final_json = {
            "generated_at": datetime.now().isoformat(),
            "summary": summary_stats,
            "developers": developer_stats
        }

        # Backup existing file if it exists
        backup_filename = backup_existing_stats_file()

        # Write to fixed JSON filename
        with open(STATS_FILENAME, 'w') as f:
            json.dump(final_json, f, indent=2, default=str)

        # Display summary table with cleaner format
        display_developer_stats_summary(developer_stats)

        # Show completion message
        if backup_filename:
            console.print(
                f"\n[bold green]Developer statistics file created: {STATS_FILENAME}[/bold green]")
            console.print(
                f"[bold yellow]Previous file backed up as: {backup_filename}[/bold yellow]")
        else:
            console.print(
                f"\n[bold green]Developer statistics file created: {STATS_FILENAME}[/bold green]")

        input("\nPress Enter to return to the menu...")
        return STATS_FILENAME


def get_jira_stats_for_assignee(cursor, assignee):
    """Get Jira statistics for a specific assignee."""
    stats = {}

    # Total issues assigned
    cursor.execute(
        f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE assignee = ?", (assignee,))
    stats["total_issues"] = cursor.fetchone()[0]

    # Issues by status
    cursor.execute(f"""
        SELECT status, COUNT(*) 
        FROM {TABLE_NAME} 
        WHERE assignee = ? 
        GROUP BY status
    """, (assignee,))
    status_counts = dict(cursor.fetchall())
    stats["issues_by_status"] = status_counts

    # Issues by priority (if priority field exists)
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if 'priority' in columns:
        cursor.execute(f"""
            SELECT priority, COUNT(*) 
            FROM {TABLE_NAME} 
            WHERE assignee = ? AND priority IS NOT NULL AND priority != ''
            GROUP BY priority
        """, (assignee,))
        priority_counts = dict(cursor.fetchall())
        stats["issues_by_priority"] = priority_counts

    # Average time in status (if created and updated fields exist)
    if 'created' in columns and 'updated' in columns:
        cursor.execute(f"""
            SELECT created, updated 
            FROM {TABLE_NAME} 
            WHERE assignee = ? AND created IS NOT NULL AND updated IS NOT NULL
        """, (assignee,))
        dates = cursor.fetchall()
        if dates:
            total_days = 0
            valid_dates = 0
            for created, updated in dates:
                try:
                    created_date = datetime.strptime(
                        created, "%Y-%m-%dT%H:%M:%S.%f%z")
                    updated_date = datetime.strptime(
                        updated, "%Y-%m-%dT%H:%M:%S.%f%z")
                    days_diff = (updated_date - created_date).days
                    if days_diff >= 0:
                        total_days += days_diff
                        valid_dates += 1
                except:
                    continue

            if valid_dates > 0:
                stats["avg_days_to_update"] = round(
                    total_days / valid_dates, 2)

    return stats


def get_git_stats_for_assignee(cursor, assignee):
    """Get Git statistics for a specific assignee by matching email or name."""
    stats = {}

    # Extract email from assignee JSON if possible
    try:
        import ast
        assignee_dict = ast.literal_eval(assignee)
        assignee_email = assignee_dict.get('emailAddress', '')
        assignee_name = assignee_dict.get('displayName', '')
    except:
        assignee_email = ''
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
        cursor.execute("""
            SELECT COUNT(*), author_name, author_email
            FROM git_commits 
            WHERE author_name LIKE ? OR author_email LIKE ?
            GROUP BY author_name, author_email
        """, (f"%{pattern}%", f"%{pattern}%"))

        matches = cursor.fetchall()
        for count, name, email in matches:
            # Avoid duplicates
            if not any(author['email'] == email for author in matching_authors):
                total_commits += count
                matching_authors.append({
                    "name": name,
                    "email": email,
                    "commits": count
                })

    stats["total_commits"] = total_commits
    stats["matching_git_authors"] = matching_authors

    # Get commit frequency (commits per day) for all matching authors
    if matching_authors:
        all_emails = [author['email'] for author in matching_authors]
        placeholders = ','.join(['?' for _ in all_emails])
        cursor.execute(f"""
            SELECT date 
            FROM git_commits 
            WHERE author_email IN ({placeholders})
            ORDER BY date
        """, all_emails)

        commit_dates = [row[0] for row in cursor.fetchall()]
        if len(commit_dates) > 1:
            try:
                first_commit = datetime.strptime(
                    commit_dates[0].split()[0], "%Y-%m-%d")
                last_commit = datetime.strptime(
                    commit_dates[-1].split()[0], "%Y-%m-%d")
                days_active = (last_commit - first_commit).days + 1
                stats["commits_per_day"] = round(
                    total_commits / days_active, 2) if days_active > 0 else 0
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
        combined["completion_rate"] = round(
            (done_count / total_jira_issues) * 100, 2)
    else:
        combined["completion_rate"] = 0

    return combined


def generate_summary_stats(developer_stats):
    """Generate summary statistics across all developers."""
    summary = {
        "total_developers": len(developer_stats),
        "total_issues": sum(dev["jira_stats"].get("total_issues", 0) for dev in developer_stats.values()),
        "total_commits": sum(dev["git_stats"].get("total_commits", 0) for dev in developer_stats.values()),
        "avg_productivity_score": 0,
        "avg_completion_rate": 0,
        "top_performers": []
    }

    if developer_stats:
        # Calculate averages
        productivity_scores = [dev["combined_stats"].get(
            "productivity_score", 0) for dev in developer_stats.values()]
        completion_rates = [dev["combined_stats"].get(
            "completion_rate", 0) for dev in developer_stats.values()]

        summary["avg_productivity_score"] = round(
            sum(productivity_scores) / len(productivity_scores), 2)
        summary["avg_completion_rate"] = round(
            sum(completion_rates) / len(completion_rates), 2)

        # Top performers by productivity score
        sorted_devs = sorted(
            developer_stats.items(),
            key=lambda x: x[1]["combined_stats"].get("productivity_score", 0),
            reverse=True
        )

        summary["top_performers"] = [
            {
                "name": name,
                "productivity_score": stats["combined_stats"].get("productivity_score", 0),
                "total_issues": stats["jira_stats"].get("total_issues", 0),
                "total_commits": stats["git_stats"].get("total_commits", 0)
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
            str(combined_stats.get("commits_per_issue", 0))
        )

    console.print("\n[bold yellow]Developer Statistics Summary:[/bold yellow]")
    console.print(table)


def display_existing_stats():
    """Display existing developer statistics from the JSON file."""
    if not os.path.exists(STATS_FILENAME):
        console.print(
            f"[bold red]No statistics file found: {STATS_FILENAME}[/bold red]")
        input("Press Enter to return to the menu...")
        return

    try:
        with open(STATS_FILENAME, 'r') as f:
            stats_data = json.load(f)

        developer_stats = stats_data.get("developers", {})
        if not developer_stats:
            console.print(
                "[bold red]No developer statistics found in the file.[/bold red]")
            input("Press Enter to return to the menu...")
            return

        # Display the summary table
        display_developer_stats_summary(developer_stats)

        # Show file info
        generated_at = stats_data.get("generated_at", "Unknown")
        console.print(
            f"\n[bold green]Statistics loaded from: {STATS_FILENAME}[/bold green]")
        console.print(
            f"[bold yellow]Generated at: {generated_at}[/bold yellow]")

        input("\nPress Enter to return to the menu...")

    except Exception as e:
        console.print(
            f"[bold red]Error reading statistics file: {str(e)}[/bold red]")
        input("Press Enter to return to the menu...")


def generate_basic_stats_json():
    """Generates a JSON file with basic time-based developer statistics."""
    from ..config import BASIC_FILENAME

    if not os.path.exists(DB_NAME):
        console.print(
            "[bold red]Database does not exist. Please update issues and commits first.[/bold red]")
        input("Press Enter to return to the menu...")
        return None

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Check if both tables exist
        cursor.execute(
            f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
        if not cursor.fetchone():
            console.print(
                "[bold red]No Jira issues data found. Please update issues first.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='git_commits'")
        if not cursor.fetchone():
            console.print(
                "[bold red]No git commits data found. Please update commits first.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        # Get all assignees from Jira issues (excluding empty/null assignees)
        cursor.execute(f"""
            SELECT DISTINCT assignee 
            FROM {TABLE_NAME} 
            WHERE assignee IS NOT NULL AND assignee != '' AND assignee != 'null'
        """)
        assignees = [row[0] for row in cursor.fetchall()]

        if not assignees:
            console.print(
                "[bold red]No assignees found in Jira issues.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        # Filter out excluded emails
        filtered_assignees = []
        for assignee in assignees:
            _, email = extract_developer_info(assignee)
            if not should_exclude_email(email):
                filtered_assignees.append(assignee)

        if not filtered_assignees:
            console.print(
                "[bold red]No assignees found after filtering excluded emails.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        developer_basic_stats = {}

        for assignee in filtered_assignees:
            stats = {
                "name": assignee,
                "commits": {
                    "last_1_day": 0,
                    "last_3_days": 0,
                    "last_7_days": 0
                },
                "jira_updates": {
                    "last_1_day": 0,
                    "last_3_days": 0,
                    "last_7_days": 0
                }
            }

            # Get commit statistics for time periods
            commit_stats = get_time_based_commit_stats(cursor, assignee)
            stats["commits"] = commit_stats

            # Get Jira update statistics for time periods
            jira_update_stats = get_time_based_jira_stats(cursor, assignee)
            stats["jira_updates"] = jira_update_stats

            developer_basic_stats[assignee] = stats

        # Create final JSON structure
        final_json = {
            "generated_at": datetime.now().isoformat(),
            "developers": developer_basic_stats
        }

        # Backup existing file if it exists
        if os.path.exists(BASIC_FILENAME):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"{BASIC_FILENAME.replace('.json', '')}_backup_{timestamp}.json"
            shutil.copy2(BASIC_FILENAME, backup_filename)
            console.print(
                f"[bold yellow]Existing basic stats file backed up to: {backup_filename}[/bold yellow]")

        # Write to basic stats JSON filename
        with open(BASIC_FILENAME, 'w') as f:
            json.dump(final_json, f, indent=2, default=str)

        # Display summary table
        display_basic_stats_summary(developer_basic_stats)

        # Show completion message
        console.print(
            f"\n[bold green]Basic statistics file created: {BASIC_FILENAME}[/bold green]")

        input("\nPress Enter to return to the menu...")
        return BASIC_FILENAME


def get_time_based_commit_stats(cursor, assignee):
    """Get commit statistics for specific time periods."""
    from datetime import datetime, timedelta

    stats = {
        "last_1_day": 0,
        "last_3_days": 0,
        "last_7_days": 0
    }

    # Extract email from assignee JSON if possible
    try:
        import ast
        assignee_dict = ast.literal_eval(assignee)
        assignee_email = assignee_dict.get('emailAddress', '')
        assignee_name = assignee_dict.get('displayName', '')
    except:
        assignee_email = ''
        assignee_name = assignee

    # Calculate date thresholds
    now = datetime.now()
    one_day_ago = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    three_days_ago = (now - timedelta(days=3)).strftime('%Y-%m-%d')
    seven_days_ago = (now - timedelta(days=7)).strftime('%Y-%m-%d')

    # Search patterns for matching commits
    search_patterns = []
    if assignee_email:
        search_patterns.append(assignee_email)
    if assignee_name:
        search_patterns.append(assignee_name)

    for pattern in search_patterns:
        # Last 1 day
        cursor.execute("""
            SELECT COUNT(*) 
            FROM git_commits 
            WHERE (author_name LIKE ? OR author_email LIKE ?) 
            AND date >= ?
        """, (f"%{pattern}%", f"%{pattern}%", one_day_ago))
        count = cursor.fetchone()[0]
        stats["last_1_day"] += count

        # Last 3 days
        cursor.execute("""
            SELECT COUNT(*) 
            FROM git_commits 
            WHERE (author_name LIKE ? OR author_email LIKE ?) 
            AND date >= ?
        """, (f"%{pattern}%", f"%{pattern}%", three_days_ago))
        count = cursor.fetchone()[0]
        stats["last_3_days"] += count

        # Last 7 days
        cursor.execute("""
            SELECT COUNT(*) 
            FROM git_commits 
            WHERE (author_name LIKE ? OR author_email LIKE ?) 
            AND date >= ?
        """, (f"%{pattern}%", f"%{pattern}%", seven_days_ago))
        count = cursor.fetchone()[0]
        stats["last_7_days"] += count

    return stats


def get_time_based_jira_stats(cursor, assignee):
    """Get Jira update statistics for specific time periods."""
    from datetime import datetime, timedelta

    stats = {
        "last_1_day": 0,
        "last_3_days": 0,
        "last_7_days": 0
    }

    # Calculate date thresholds
    now = datetime.now()
    one_day_ago = (now - timedelta(days=1)).isoformat()
    three_days_ago = (now - timedelta(days=3)).isoformat()
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    # Check if updated column exists
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if 'updated' in columns:
        # Last 1 day
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM {TABLE_NAME} 
            WHERE assignee = ? AND updated >= ?
        """, (assignee, one_day_ago))
        stats["last_1_day"] = cursor.fetchone()[0]

        # Last 3 days
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM {TABLE_NAME} 
            WHERE assignee = ? AND updated >= ?
        """, (assignee, three_days_ago))
        stats["last_3_days"] = cursor.fetchone()[0]

        # Last 7 days
        cursor.execute(f"""
            SELECT COUNT(*) 
            FROM {TABLE_NAME} 
            WHERE assignee = ? AND updated >= ?
        """, (assignee, seven_days_ago))
        stats["last_7_days"] = cursor.fetchone()[0]

    return stats


def display_basic_stats_summary(developer_basic_stats):
    """Display a summary table of basic developer statistics."""
    table = Table(show_header=True, header_style="bold green")
    table.add_column("Developer")
    table.add_column("Email")
    table.add_column("Commits (1d)")
    table.add_column("Commits (3d)")
    table.add_column("Commits (7d)")
    table.add_column("Jira Updates (1d)")
    table.add_column("Jira Updates (3d)")
    table.add_column("Jira Updates (7d)")

    for assignee_json, stats in developer_basic_stats.items():
        # Extract clean name and email for display
        name, email = extract_developer_info(assignee_json)

        table.add_row(
            name,
            email,
            str(stats["commits"]["last_1_day"]),
            str(stats["commits"]["last_3_days"]),
            str(stats["commits"]["last_7_days"]),
            str(stats["jira_updates"]["last_1_day"]),
            str(stats["jira_updates"]["last_3_days"]),
            str(stats["jira_updates"]["last_7_days"])
        )

    console.print(
        "\n[bold yellow]Basic Developer Statistics Summary:[/bold yellow]")
    console.print(table)


def display_existing_basic_stats():
    """Display existing basic developer statistics from the JSON file."""
    from ..config import BASIC_FILENAME

    if not os.path.exists(BASIC_FILENAME):
        console.print(
            f"[bold red]No basic statistics file found: {BASIC_FILENAME}[/bold red]")
        input("Press Enter to return to the menu...")
        return

    try:
        with open(BASIC_FILENAME, 'r') as f:
            stats_data = json.load(f)

        developer_stats = stats_data.get("developers", {})
        if not developer_stats:
            console.print(
                "[bold red]No developer statistics found in the file.[/bold red]")
            input("Press Enter to return to the menu...")
            return

        # Display the summary table
        display_basic_stats_summary(developer_stats)

        # Show file info
        generated_at = stats_data.get("generated_at", "Unknown")
        console.print(
            f"\n[bold green]Basic statistics loaded from: {BASIC_FILENAME}[/bold green]")
        console.print(
            f"[bold yellow]Generated at: {generated_at}[/bold yellow]")

        input("\nPress Enter to return to the menu...")

    except Exception as e:
        console.print(
            f"[bold red]Error reading basic statistics file: {str(e)}[/bold red]")
        input("Press Enter to return to the menu...")
