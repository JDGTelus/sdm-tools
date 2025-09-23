"""Statistics generation functionality."""
import os
import sqlite3
import json
import shutil
from datetime import datetime
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from ..config import DB_NAME, TABLE_NAME, BASIC_STATS, EXCLUDED_EMAILS

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
        if 'self' in watches_dict:
            url = watches_dict['self']
            # Split by '/' and get the part before '/watchers'
            parts = url.split('/')
            if len(parts) >= 2:
                # Look for the issue code in the URL path
                for part in parts:
                    if part.startswith('SET-') and len(part) > 4:
                        # Validate it looks like SET-XXXXX format (SET- followed by digits)
                        # Get part after 'SET-'
                        issue_part = part.split('-', 1)[1]
                        if issue_part.isdigit():
                            return part
    except (ValueError, AttributeError, TypeError, SyntaxError) as e:
        # If parsing fails, return None
        pass

    return None


def backup_existing_stats_file():
    """Backup existing basic stats file if it exists."""
    if os.path.exists(BASIC_STATS):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Ensure backup is created in the same directory as the stats file
        stats_dir = os.path.dirname(BASIC_STATS)
        backup_filename = os.path.join(
            stats_dir, f"team_basic_stats_backup_{timestamp}.json")
        shutil.copy2(BASIC_STATS, backup_filename)
        console.print(
            f"[bold yellow]Existing basic stats file backed up to: {backup_filename}[/bold yellow]")
        return backup_filename
    return None


def backup_existing_developer_stats_file():
    """Backup existing developer stats file if it exists."""
    from ..config import SIMPLE_STATS

    if os.path.exists(SIMPLE_STATS):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Ensure backup is created in the same directory as the stats file
        stats_dir = os.path.dirname(SIMPLE_STATS)
        backup_filename = os.path.join(
            stats_dir, f"team_simple_stats_backup_{timestamp}.json")
        shutil.copy2(SIMPLE_STATS, backup_filename)
        console.print(
            f"[bold yellow]Existing developer stats file backed up to: {backup_filename}[/bold yellow]")
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
    from ..config import SIMPLE_STATS

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
        backup_filename = backup_existing_developer_stats_file()

        # Write to developer stats JSON filename
        with open(SIMPLE_STATS, 'w') as f:
            json.dump(final_json, f, indent=2, default=str)

        # Display summary table with cleaner format
        display_developer_stats_summary(developer_stats)

        # Show completion message
        if backup_filename:
            console.print(
                f"\n[bold green]Developer statistics file created: {SIMPLE_STATS}[/bold green]")
            console.print(
                f"[bold yellow]Previous file backed up as: {backup_filename}[/bold yellow]")
        else:
            console.print(
                f"\n[bold green]Developer statistics file created: {SIMPLE_STATS}[/bold green]")

        try:
            input("\nPress Enter to return to the menu...")
        except EOFError:
            pass
        return SIMPLE_STATS


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

    # Check what columns are available
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    # Issues by priority (if priority field exists)
    if 'priority' in columns:
        cursor.execute(f"""
            SELECT priority, COUNT(*) 
            FROM {TABLE_NAME} 
            WHERE assignee = ? AND priority IS NOT NULL AND priority != ''
            GROUP BY priority
        """, (assignee,))
        priority_counts = dict(cursor.fetchall())
        stats["issues_by_priority"] = priority_counts

    # Total story points (if customfield_10026 exists)
    if 'customfield_10026' in columns:
        cursor.execute(f"""
            SELECT SUM(CAST(customfield_10026 AS REAL)) 
            FROM {TABLE_NAME} 
            WHERE assignee = ? AND customfield_10026 IS NOT NULL AND customfield_10026 != ''
        """, (assignee,))
        result = cursor.fetchone()[0]
        stats["total_story_points"] = round(result, 1) if result else 0

    # Story points by status (if customfield_10026 exists)
    if 'customfield_10026' in columns:
        cursor.execute(f"""
            SELECT status, SUM(CAST(customfield_10026 AS REAL)) 
            FROM {TABLE_NAME} 
            WHERE assignee = ? AND customfield_10026 IS NOT NULL AND customfield_10026 != ''
            GROUP BY status
        """, (assignee,))
        story_points_by_status = dict(cursor.fetchall())
        # Round the values
        stats["story_points_by_status"] = {
            k: round(v, 1) if v else 0 for k, v in story_points_by_status.items()}

    # Issues by label (if customfield_10014 exists)
    if 'customfield_10014' in columns:
        cursor.execute(f"""
            SELECT customfield_10014, COUNT(*) 
            FROM {TABLE_NAME} 
            WHERE assignee = ? AND customfield_10014 IS NOT NULL AND customfield_10014 != ''
            GROUP BY customfield_10014
        """, (assignee,))
        label_counts = dict(cursor.fetchall())
        stats["issues_by_label"] = label_counts

    # Extract issue codes from watches field (if watches field exists)
    if 'watches' in columns:
        cursor.execute(f"""
            SELECT watches 
            FROM {TABLE_NAME} 
            WHERE assignee = ? AND watches IS NOT NULL AND watches != ''
        """, (assignee,))
        watches_data = cursor.fetchall()

        issue_codes = []
        for (watches_json,) in watches_data:
            issue_code = extract_issue_code_from_watches(watches_json)
            if issue_code:
                issue_codes.append(issue_code)

        stats["issue_codes"] = issue_codes

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
    from ..config import SIMPLE_STATS

    if not os.path.exists(SIMPLE_STATS):
        console.print(
            f"[bold red]No statistics file found: {SIMPLE_STATS}[/bold red]")
        input("Press Enter to return to the menu...")
        return

    try:
        with open(SIMPLE_STATS, 'r') as f:
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
            f"\n[bold green]Statistics loaded from: {SIMPLE_STATS}[/bold green]")
        console.print(
            f"[bold yellow]Generated at: {generated_at}[/bold yellow]")

        try:
            input("\nPress Enter to return to the menu...")
        except EOFError:
            pass

    except Exception as e:
        console.print(
            f"[bold red]Error reading statistics file: {str(e)}[/bold red]")
        try:
            input("Press Enter to return to the menu...")
        except EOFError:
            pass


def generate_basic_stats_json():
    """Generates a JSON file with unified developer statistics (total commits, jira updates, and story points)."""
    from ..config import BASIC_STATS

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
            # Extract clean name for display
            name, email = extract_developer_info(assignee)

            stats = {
                "name": name,
                "total_commits": 0,
                "total_jira_updates": 0,
                "total_story_points_closed": 0
            }

            # Get unified commit statistics
            total_commits = get_unified_commit_stats(cursor, assignee)
            stats["total_commits"] = total_commits

            # Get unified Jira update statistics
            total_jira_updates = get_unified_jira_stats(cursor, assignee)
            stats["total_jira_updates"] = total_jira_updates

            # Get unified story points for closed stories
            total_story_points = get_unified_story_points_stats(
                cursor, assignee)
            stats["total_story_points_closed"] = total_story_points

            # Get issue codes for this assignee
            issue_codes = get_issue_codes_for_assignee(cursor, assignee)
            stats["issue_codes"] = issue_codes

            # Use the clean name as the key instead of the full JSON string
            developer_basic_stats[name] = stats

        # Create final JSON structure
        final_json = {
            "generated_at": datetime.now().isoformat(),
            "developers": developer_basic_stats
        }

        # Backup existing file if it exists
        if os.path.exists(BASIC_STATS):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            # Ensure backup is created in the same directory as the basic stats file
            basic_stats_dir = os.path.dirname(BASIC_STATS)
            backup_filename = os.path.join(
                basic_stats_dir, f"{os.path.basename(BASIC_STATS).replace('.json', '')}_backup_{timestamp}.json")
            shutil.copy2(BASIC_STATS, backup_filename)
            console.print(
                f"[bold yellow]Existing basic stats file backed up to: {backup_filename}[/bold yellow]")

        # Write to basic stats JSON filename
        with open(BASIC_STATS, 'w') as f:
            json.dump(final_json, f, indent=2, default=str)

        # Display summary table
        display_basic_stats_summary(developer_basic_stats)

        # Show completion message
        console.print(
            f"\n[bold green]Basic statistics file created: {BASIC_STATS}[/bold green]")

        input("\nPress Enter to return to the menu...")
        return BASIC_STATS


def get_time_based_commit_stats(cursor, assignee):
    """Get commit statistics for specific time periods."""
    from datetime import datetime, timedelta
    import re

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

    cursor.execute(f"""
        SELECT DISTINCT date 
        FROM git_commits 
        WHERE {where_clause}
    """, search_params)

    commit_dates = cursor.fetchall()

    for (date_str,) in commit_dates:
        try:
            # Parse git date format: "Wed Sep 17 23:37:12 2025 +0000"
            # Remove timezone info and parse
            date_clean = re.sub(r'\s+[+-]\d{4}$', '', date_str)
            commit_date = datetime.strptime(date_clean, '%a %b %d %H:%M:%S %Y')

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
                f"[bold yellow]Warning: Could not parse date '{date_str}': {e}[/bold yellow]")
            continue

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


def get_time_based_story_points_stats(cursor, assignee):
    """Get story points statistics for closed stories in specific time periods."""
    from datetime import datetime, timedelta

    stats = {
        "last_1_day": 0,
        "last_3_days": 0,
        "last_7_days": 0
    }

    # Check if required columns exist
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if 'customfield_10026' not in columns or 'updated' not in columns or 'status' not in columns:
        return stats

    # Calculate date thresholds
    now = datetime.now()
    one_day_ago = (now - timedelta(days=1)).isoformat()
    three_days_ago = (now - timedelta(days=3)).isoformat()
    seven_days_ago = (now - timedelta(days=7)).isoformat()

    # Common "closed" status indicators
    closed_statuses = ["Done", "Closed", "Resolved", "Complete", "Completed"]
    status_placeholders = ','.join(['?' for _ in closed_statuses])

    # Last 1 day - sum of story points for closed stories
    cursor.execute(f"""
        SELECT SUM(CAST(customfield_10026 AS REAL)) 
        FROM {TABLE_NAME} 
        WHERE assignee = ? 
        AND updated >= ? 
        AND status IN ({status_placeholders})
        AND customfield_10026 IS NOT NULL 
        AND customfield_10026 != ''
    """, (assignee, one_day_ago, *closed_statuses))
    result = cursor.fetchone()[0]
    stats["last_1_day"] = round(result, 1) if result else 0

    # Last 3 days
    cursor.execute(f"""
        SELECT SUM(CAST(customfield_10026 AS REAL)) 
        FROM {TABLE_NAME} 
        WHERE assignee = ? 
        AND updated >= ? 
        AND status IN ({status_placeholders})
        AND customfield_10026 IS NOT NULL 
        AND customfield_10026 != ''
    """, (assignee, three_days_ago, *closed_statuses))
    result = cursor.fetchone()[0]
    stats["last_3_days"] = round(result, 1) if result else 0

    # Last 7 days
    cursor.execute(f"""
        SELECT SUM(CAST(customfield_10026 AS REAL)) 
        FROM {TABLE_NAME} 
        WHERE assignee = ? 
        AND updated >= ? 
        AND status IN ({status_placeholders})
        AND customfield_10026 IS NOT NULL 
        AND customfield_10026 != ''
    """, (assignee, seven_days_ago, *closed_statuses))
    result = cursor.fetchone()[0]
    stats["last_7_days"] = round(result, 1) if result else 0

    return stats


def get_unified_commit_stats(cursor, assignee):
    """Get total commit statistics for an assignee."""
    # Extract email from assignee JSON if possible
    try:
        import ast
        assignee_dict = ast.literal_eval(assignee)
        assignee_email = assignee_dict.get('emailAddress', '')
        assignee_name = assignee_dict.get('displayName', '')
    except:
        assignee_email = ''
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

    cursor.execute(f"""
        SELECT COUNT(DISTINCT hash) 
        FROM git_commits 
        WHERE {where_clause}
    """, search_params)

    result = cursor.fetchone()
    return result[0] if result else 0


def get_unified_jira_stats(cursor, assignee):
    """Get total Jira update statistics for an assignee."""
    # Check if updated column exists
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if 'updated' not in columns:
        return 0

    # Count all Jira updates for this assignee
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM {TABLE_NAME} 
        WHERE assignee = ?
    """, (assignee,))

    result = cursor.fetchone()
    return result[0] if result else 0


def get_unified_story_points_stats(cursor, assignee):
    """Get total story points for closed stories for an assignee."""
    # Check if required columns exist
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if 'customfield_10026' not in columns or 'status' not in columns:
        return 0

    # Common "closed" status indicators
    closed_statuses = ["Done", "Closed", "Resolved", "Complete", "Completed"]
    status_placeholders = ','.join(['?' for _ in closed_statuses])

    # Sum of story points for closed stories
    cursor.execute(f"""
        SELECT SUM(CAST(customfield_10026 AS REAL)) 
        FROM {TABLE_NAME} 
        WHERE assignee = ? 
        AND status IN ({status_placeholders})
        AND customfield_10026 IS NOT NULL 
        AND customfield_10026 != ''
    """, (assignee, *closed_statuses))

    result = cursor.fetchone()[0]
    return round(result, 1) if result else 0


def get_issue_codes_for_assignee(cursor, assignee):
    """Get issue codes for a specific assignee from the watches field."""
    # Check if watches column exists
    cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in cursor.fetchall()]

    if 'watches' not in columns:
        return []

    # Get watches data for this assignee
    cursor.execute(f"""
        SELECT watches 
        FROM {TABLE_NAME} 
        WHERE assignee = ? AND watches IS NOT NULL AND watches != ''
    """, (assignee,))
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
            str(stats["total_story_points_closed"])
        )

    console.print(
        "\n[bold yellow]Unified Developer Statistics Summary:[/bold yellow]")
    console.print(table)


def display_existing_basic_stats():
    """Display existing basic developer statistics from the JSON file."""
    from ..config import BASIC_STATS

    if not os.path.exists(BASIC_STATS):
        console.print(
            f"[bold red]No basic statistics file found: {BASIC_STATS}[/bold red]")
        input("Press Enter to return to the menu...")
        return

    try:
        with open(BASIC_STATS, 'r') as f:
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
            f"\n[bold green]Basic statistics loaded from: {BASIC_STATS}[/bold green]")
        console.print(
            f"[bold yellow]Generated at: {generated_at}[/bold yellow]")

        input("\nPress Enter to return to the menu...")

    except Exception as e:
        console.print(
            f"[bold red]Error reading basic statistics file: {str(e)}[/bold red]")
        input("Press Enter to return to the menu...")


def generate_sprint_stats_json():
    """Generates a JSON file with sprint-based developer statistics combining issues, commits, and sprints data."""
    sprint_stats_file = "ux/web/data/team_sprint_stats.json"

    if not os.path.exists(DB_NAME):
        console.print(
            "[bold red]Database does not exist. Please update issues and commits first.[/bold red]")
        input("Press Enter to return to the menu...")
        return None

    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()

        # Check if all required tables exist
        required_tables = [TABLE_NAME, 'git_commits', f'{TABLE_NAME}_sprints']
        for table in required_tables:
            cursor.execute(
                f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if not cursor.fetchone():
                console.print(
                    f"[bold red]Required table '{table}' not found. Please ensure all data is loaded.[/bold red]")
                input("Press Enter to return to the menu...")
                return None

        # Get all sprints
        cursor.execute(
            f"SELECT id, name, state, startDate, endDate FROM {TABLE_NAME}_sprints ORDER BY startDate")
        sprints = cursor.fetchall()

        if not sprints:
            console.print(
                "[bold red]No sprints found in the database.[/bold red]")
            input("Press Enter to return to the menu...")
            return None

        # Get all assignees from Jira issues (excluding empty/null assignees)
        cursor.execute(f"""
            SELECT DISTINCT assignee 
            FROM {TABLE_NAME} 
            WHERE assignee IS NOT NULL AND assignee != '' AND assignee != 'null'
        """)
        assignees = [row[0] for row in cursor.fetchall()]

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

        sprint_analytics = {}

        for sprint_id, sprint_name, sprint_state, start_date, end_date in sprints:
            sprint_key = f"{sprint_id}_{sprint_name.replace(' ', '_')}"

            sprint_analytics[sprint_key] = {
                "sprint_info": {
                    "id": sprint_id,
                    "name": sprint_name,
                    "state": sprint_state,
                    "start_date": start_date,
                    "end_date": end_date
                },
                "developers": {}
            }

            # Get stats for each developer in this sprint
            for assignee in filtered_assignees:
                name, email = extract_developer_info(assignee)

                # Get sprint-specific stats for this developer
                sprint_stats = get_sprint_stats_for_developer(
                    cursor, assignee, sprint_id, start_date, end_date)

                # Only include developers who have activity in this sprint
                if (sprint_stats["commits_in_sprint"] > 0 or
                    sprint_stats["issues_assigned_in_sprint"] > 0 or
                        sprint_stats["issues_closed_in_sprint"] > 0):

                    sprint_analytics[sprint_key]["developers"][name] = {
                        "name": name,
                        "email": email,
                        "commits_in_sprint": sprint_stats["commits_in_sprint"],
                        "issues_assigned_in_sprint": sprint_stats["issues_assigned_in_sprint"],
                        "issues_closed_in_sprint": sprint_stats["issues_closed_in_sprint"],
                        "story_points_closed_in_sprint": sprint_stats["story_points_closed_in_sprint"]
                    }

        # Create final JSON structure
        final_json = {
            "generated_at": datetime.now().isoformat(),
            "sprint_analytics": sprint_analytics
        }

        # Backup existing file if it exists
        if os.path.exists(sprint_stats_file):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            stats_dir = os.path.dirname(sprint_stats_file)
            backup_filename = os.path.join(
                stats_dir, f"team_sprint_stats_backup_{timestamp}.json")
            shutil.copy2(sprint_stats_file, backup_filename)
            console.print(
                f"[bold yellow]Existing sprint stats file backed up to: {backup_filename}[/bold yellow]")

        # Ensure directory exists
        os.makedirs(os.path.dirname(sprint_stats_file), exist_ok=True)

        # Write to sprint stats JSON file
        with open(sprint_stats_file, 'w') as f:
            json.dump(final_json, f, indent=2, default=str)

        # Display summary
        display_sprint_stats_summary(sprint_analytics)

        console.print(
            f"\n[bold green]Sprint statistics file created: {sprint_stats_file}[/bold green]")

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
        "story_points_closed_in_sprint": 0
    }

    # Extract developer info - handle JSON string format
    try:
        import json
        assignee_dict = json.loads(assignee)
        assignee_email = assignee_dict.get('emailAddress', '')
        assignee_name = assignee_dict.get('displayName', '')
    except (json.JSONDecodeError, TypeError):
        # Fallback to ast.literal_eval for older format
        try:
            import ast
            assignee_dict = ast.literal_eval(assignee)
            assignee_email = assignee_dict.get('emailAddress', '')
            assignee_name = assignee_dict.get('displayName', '')
        except:
            assignee_email = ''
            assignee_name = assignee

    # Parse sprint dates - handle different timezone formats
    try:
        if start_date:
            # Handle both 'Z' and '+00:00' timezone formats
            start_date_clean = start_date.replace('Z', '+00:00')
            sprint_start = datetime.fromisoformat(start_date_clean)
        else:
            sprint_start = None

        if end_date:
            end_date_clean = end_date.replace('Z', '+00:00')
            sprint_end = datetime.fromisoformat(end_date_clean)
        else:
            sprint_end = None
    except Exception as e:
        console.print(
            f"[bold yellow]Warning: Could not parse sprint dates for sprint {sprint_id}: {e}[/bold yellow]")
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

        # Get all commits with dates for this developer
        cursor.execute(f"""
            SELECT DISTINCT hash, date 
            FROM git_commits 
            WHERE ({where_clause}) AND date IS NOT NULL
        """, search_params)

        commit_data = cursor.fetchall()
        commits_in_range = 0

        for hash_val, date_str in commit_data:
            try:
                # Parse git date format: "Wed Sep 17 23:37:12 2025 +0000" or similar
                # Remove timezone info and parse
                date_clean = re.sub(r'\s+[+-]\d{4}$', '', date_str.strip())

                # Try different date formats
                commit_date = None
                date_formats = [
                    '%a %b %d %H:%M:%S %Y',  # Wed Sep 17 23:37:12 2025
                    '%Y-%m-%d %H:%M:%S',     # 2025-09-17 23:37:12
                    '%Y-%m-%d',              # 2025-09-17
                ]

                for fmt in date_formats:
                    try:
                        commit_date = datetime.strptime(date_clean, fmt)
                        break
                    except ValueError:
                        continue

                if commit_date and sprint_start <= commit_date <= sprint_end:
                    commits_in_range += 1

            except Exception as e:
                # Skip commits with unparseable dates
                continue

        stats["commits_in_sprint"] = commits_in_range

    # 2. Get issues assigned to developer that are in this sprint
    cursor.execute(f"""
        SELECT COUNT(*) 
        FROM {TABLE_NAME} 
        WHERE assignee = ? AND customfield_10020 LIKE ?
    """, (assignee, f'%{sprint_id}%'))

    stats["issues_assigned_in_sprint"] = cursor.fetchone()[0]

    # 3. Get issues closed during sprint period - Fix status JSON parsing
    closed_statuses = ["Done", "Closed", "Resolved", "Complete", "Completed"]

    if sprint_start and sprint_end:
        sprint_start_str = sprint_start.isoformat()
        sprint_end_str = sprint_end.isoformat()

        # Get all issues for this assignee in this sprint within date range
        cursor.execute(f"""
            SELECT status, customfield_10026
            FROM {TABLE_NAME} 
            WHERE assignee = ? 
            AND customfield_10020 LIKE ?
            AND updated >= ? AND updated <= ?
        """, (assignee, f'%{sprint_id}%', sprint_start_str, sprint_end_str))

        issues_data = cursor.fetchall()
        closed_count = 0
        total_story_points = 0

        for status_json, story_points_str in issues_data:
            try:
                # Parse status JSON to get actual status name
                status_dict = json.loads(status_json)
                status_name = status_dict.get('name', '')

                if status_name in closed_statuses:
                    closed_count += 1

                    # Add story points if available
                    if story_points_str and story_points_str.strip() and story_points_str != 'null':
                        try:
                            story_points_value = float(
                                story_points_str.strip())
                            total_story_points += story_points_value
                        except (ValueError, TypeError):
                            continue

            except (json.JSONDecodeError, TypeError):
                # Try fallback parsing for status
                try:
                    import ast
                    status_dict = ast.literal_eval(status_json)
                    status_name = status_dict.get('name', '')

                    if status_name in closed_statuses:
                        closed_count += 1

                        # Add story points if available
                        if story_points_str and story_points_str.strip() and story_points_str != 'null':
                            try:
                                story_points_value = float(
                                    story_points_str.strip())
                                total_story_points += story_points_value
                            except (ValueError, TypeError):
                                continue
                except:
                    continue

        stats["issues_closed_in_sprint"] = closed_count
        stats["story_points_closed_in_sprint"] = round(total_story_points, 1)
    else:
        # If no date range, just check for closed issues in the sprint
        cursor.execute(f"""
            SELECT status, customfield_10026
            FROM {TABLE_NAME} 
            WHERE assignee = ? 
            AND customfield_10020 LIKE ?
        """, (assignee, f'%{sprint_id}%'))

        issues_data = cursor.fetchall()
        closed_count = 0
        total_story_points = 0

        for status_json, story_points_str in issues_data:
            try:
                # Parse status JSON to get actual status name
                status_dict = json.loads(status_json)
                status_name = status_dict.get('name', '')

                if status_name in closed_statuses:
                    closed_count += 1

                    # Add story points if available
                    if story_points_str and story_points_str.strip() and story_points_str != 'null':
                        try:
                            story_points_value = float(
                                story_points_str.strip())
                            total_story_points += story_points_value
                        except (ValueError, TypeError):
                            continue

            except (json.JSONDecodeError, TypeError):
                # Try fallback parsing for status
                try:
                    import ast
                    status_dict = ast.literal_eval(status_json)
                    status_name = status_dict.get('name', '')

                    if status_name in closed_statuses:
                        closed_count += 1

                        # Add story points if available
                        if story_points_str and story_points_str.strip() and story_points_str != 'null':
                            try:
                                story_points_value = float(
                                    story_points_str.strip())
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
            f"\n[bold cyan]Sprint: {sprint_info['name']} ({sprint_info['state']})[/bold cyan]")

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
                str(dev_stats["story_points_closed_in_sprint"])
            )

        console.print(table)


def display_existing_sprint_stats():
    """Display existing sprint statistics from the JSON file."""
    sprint_stats_file = "ux/web/data/team_sprint_stats.json"

    if not os.path.exists(sprint_stats_file):
        console.print(
            f"[bold red]No sprint statistics file found: {sprint_stats_file}[/bold red]")
        input("Press Enter to return to the menu...")
        return

    try:
        with open(sprint_stats_file, 'r') as f:
            stats_data = json.load(f)

        sprint_analytics = stats_data.get("sprint_analytics", {})
        if not sprint_analytics:
            console.print(
                "[bold red]No sprint analytics found in the file.[/bold red]")
            input("Press Enter to return to the menu...")
            return

        # Display the sprint analytics
        display_sprint_stats_summary(sprint_analytics)

        # Show file info
        generated_at = stats_data.get("generated_at", "Unknown")
        console.print(
            f"\n[bold green]Sprint statistics loaded from: {sprint_stats_file}[/bold green]")
        console.print(
            f"[bold yellow]Generated at: {generated_at}[/bold yellow]")

        input("\nPress Enter to return to the menu...")

    except Exception as e:
        console.print(
            f"[bold red]Error reading sprint statistics file: {str(e)}[/bold red]")
        input("Press Enter to return to the menu...")
