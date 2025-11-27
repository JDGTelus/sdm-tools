"""Issue normalization for normalized database."""

from rich.console import Console

from ...config import TABLE_NAME
from ...utils import get_local_timezone, parse_jira_date_to_local
from .developer_normalizer import find_developer_id_by_email
from .email_normalizer import extract_developer_from_jira_json

console = Console()


def normalize_issues(old_conn, new_conn):
    """Extract and normalize issue data.

    Args:
        old_conn: Connection to old database
        new_conn: Connection to new normalized database

    Returns:
        Count of issues processed
    """
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # Check if table exists
    old_cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{TABLE_NAME}'")
    if not old_cursor.fetchone():
        console.print(f"[bold red]Table {TABLE_NAME} not found[/bold red]")
        return 0

    # Get table columns
    old_cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in old_cursor.fetchall()]

    # Build SELECT query for available fields
    fields = ["id", "summary", "status", "assignee", "creator", "created", "updated"]
    if "statuscategorychangedate" in columns:
        fields.append("statuscategorychangedate")

    # Try to find story points field (common Jira customfields)
    story_points_field = None
    for possible_field in [
        "customfield_10016",
        "customfield_10026",
        "customfield_10002",
        "customfield_10004",
    ]:
        if possible_field in columns:
            story_points_field = possible_field
            fields.append(possible_field)
            break

    query = f"SELECT {', '.join(fields)} FROM {TABLE_NAME}"
    old_cursor.execute(query)

    tz = get_local_timezone()
    count = 0

    for row in old_cursor.fetchall():
        issue_id = row[0]
        summary = row[1] if len(row) > 1 else None
        status_json = row[2] if len(row) > 2 else None
        assignee_json = row[3] if len(row) > 3 else None
        creator_json = row[4] if len(row) > 4 else None
        created = row[5] if len(row) > 5 else None
        updated = row[6] if len(row) > 6 else None
        status_changed = row[7] if len(row) > 7 and "statuscategorychangedate" in columns else None

        # Extract story points if field exists
        story_points = None
        if story_points_field:
            story_points_idx = 7 if "statuscategorychangedate" in columns else 6
            story_points_idx += 1  # Adjust for story points field position
            story_points_raw = row[story_points_idx] if len(row) > story_points_idx else None
            if story_points_raw is not None:
                try:
                    story_points = float(story_points_raw)
                except (ValueError, TypeError):
                    story_points = None

        # Extract status name from JSON
        status_name = None
        if status_json:
            try:
                import ast

                status_dict = ast.literal_eval(status_json)
                status_name = status_dict.get("name", "")
            except:
                pass

        # Find developer IDs
        assignee_email, _, _ = extract_developer_from_jira_json(assignee_json)
        creator_email, _, _ = extract_developer_from_jira_json(creator_json)

        assignee_id = (
            find_developer_id_by_email(new_conn, assignee_email) if assignee_email else None
        )
        creator_id = find_developer_id_by_email(new_conn, creator_email) if creator_email else None

        # Parse dates to local
        created_dt = parse_jira_date_to_local(created, tz) if created else None
        updated_dt = parse_jira_date_to_local(updated, tz) if updated else None
        status_changed_dt = parse_jira_date_to_local(status_changed, tz) if status_changed else None

        created_date_local = created_dt.date().isoformat() if created_dt else None
        updated_date_local = updated_dt.date().isoformat() if updated_dt else None
        status_changed_date_local = (
            status_changed_dt.date().isoformat() if status_changed_dt else None
        )

        # Insert issue
        new_cursor.execute(
            """
            INSERT INTO issues (
                id, summary, status_name, story_points, assignee_id, creator_id,
                created_at, updated_at, created_date_local, updated_date_local,
                status_changed_at, status_changed_date_local
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                issue_id,
                summary,
                status_name,
                story_points,
                assignee_id,
                creator_id,
                created,
                updated,
                created_date_local,
                updated_date_local,
                status_changed,
                status_changed_date_local,
            ),
        )

        count += 1

    new_conn.commit()
    console.print(f"[bold green]✓ Normalized {count} issues[/bold green]")

    return count


def link_issues_to_sprints(old_conn, new_conn):
    """Extract issue-sprint relationships from customfield_10020.

    Args:
        old_conn: Connection to old database
        new_conn: Connection to new database

    Returns:
        Count of relationships created
    """
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # Check if customfield_10020 exists
    old_cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in old_cursor.fetchall()]

    if "customfield_10020" not in columns:
        console.print("[bold yellow]No customfield_10020 (sprint field) found[/bold yellow]")
        return 0

    old_cursor.execute(
        f"SELECT id, customfield_10020 FROM {TABLE_NAME} WHERE customfield_10020 IS NOT NULL AND customfield_10020 != ''"
    )

    count = 0

    for row in old_cursor.fetchall():
        issue_id, sprint_json = row

        try:
            import ast
            import json

            # Try JSON first, then ast.literal_eval
            try:
                sprint_list = json.loads(sprint_json)
            except json.JSONDecodeError:
                sprint_list = ast.literal_eval(sprint_json)

            # Handle both single sprint and list of sprints
            if isinstance(sprint_list, list):
                for sprint in sprint_list:
                    if isinstance(sprint, dict) and "id" in sprint:
                        new_cursor.execute(
                            """
                            INSERT OR IGNORE INTO issue_sprints (issue_id, sprint_id)
                            VALUES (?, ?)
                        """,
                            (issue_id, sprint["id"]),
                        )
                        count += 1
            elif isinstance(sprint_list, dict) and "id" in sprint_list:
                new_cursor.execute(
                    """
                    INSERT OR IGNORE INTO issue_sprints (issue_id, sprint_id)
                    VALUES (?, ?)
                """,
                    (issue_id, sprint_list["id"]),
                )
                count += 1

        except Exception:
            pass  # Skip malformed sprint data

    new_conn.commit()
    console.print(f"[bold green]✓ Linked {count} issue-sprint relationships[/bold green]")

    return count
