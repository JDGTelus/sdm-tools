"""Jira event extraction for normalized database."""

from rich.console import Console

from ...config import TABLE_NAME
from ...utils import get_local_timezone, get_time_bucket, parse_jira_date_to_local
from .developer_normalizer import find_developer_id_by_email
from .email_normalizer import extract_developer_from_jira_json
from .sprint_normalizer import find_sprint_for_date

console = Console()


def extract_jira_events(old_conn, new_conn, sprint_date_map):
    """Extract Jira activity events from issues table.

    Creates events for:
        - Issue created
        - Issue updated
        - Status changed

    Args:
        old_conn: Connection to old database
        new_conn: Connection to new normalized database
        sprint_date_map: List of sprint date ranges

    Returns:
        Count of events created
    """
    old_cursor = old_conn.cursor()
    new_cursor = new_conn.cursor()

    # Get all issues with timestamps
    old_cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
    columns = [info[1] for info in old_cursor.fetchall()]

    fields = ["id", "creator", "created", "assignee", "updated"]
    if "statuscategorychangedate" in columns:
        fields.append("statuscategorychangedate")

    query = f"SELECT {', '.join(fields)} FROM {TABLE_NAME}"
    old_cursor.execute(query)

    tz = get_local_timezone()
    count = 0

    for row in old_cursor.fetchall():
        issue_id = row[0]
        creator_json = row[1] if len(row) > 1 else None
        created = row[2] if len(row) > 2 else None
        assignee_json = row[3] if len(row) > 3 else None
        updated = row[4] if len(row) > 4 else None
        status_changed = row[5] if len(row) > 5 and "statuscategorychangedate" in columns else None

        # EVENT 1: Issue Created
        if created and creator_json:
            creator_email, _, _ = extract_developer_from_jira_json(creator_json)
            creator_id = find_developer_id_by_email(new_conn, creator_email)

            if creator_id:
                created_dt = parse_jira_date_to_local(created, tz)
                if created_dt:
                    event_date = created_dt.date()
                    event_hour = created_dt.hour
                    time_bucket = get_time_bucket(created_dt)
                    sprint_id = find_sprint_for_date(event_date, sprint_date_map)

                    new_cursor.execute(
                        """
                        INSERT INTO jira_events (
                            developer_id, event_type, event_timestamp, event_date,
                            event_hour, time_bucket, issue_id, sprint_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            creator_id,
                            "created",
                            created,
                            event_date.isoformat(),
                            event_hour,
                            time_bucket,
                            issue_id,
                            sprint_id,
                        ),
                    )
                    count += 1

        # EVENT 2: Issue Updated
        if updated and assignee_json:
            assignee_email, _, _ = extract_developer_from_jira_json(assignee_json)
            assignee_id = find_developer_id_by_email(new_conn, assignee_email)

            if assignee_id:
                updated_dt = parse_jira_date_to_local(updated, tz)
                if updated_dt:
                    event_date = updated_dt.date()
                    event_hour = updated_dt.hour
                    time_bucket = get_time_bucket(updated_dt)
                    sprint_id = find_sprint_for_date(event_date, sprint_date_map)

                    new_cursor.execute(
                        """
                        INSERT INTO jira_events (
                            developer_id, event_type, event_timestamp, event_date,
                            event_hour, time_bucket, issue_id, sprint_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            assignee_id,
                            "updated",
                            updated,
                            event_date.isoformat(),
                            event_hour,
                            time_bucket,
                            issue_id,
                            sprint_id,
                        ),
                    )
                    count += 1

        # EVENT 3: Status Changed
        if status_changed and assignee_json:
            assignee_email, _, _ = extract_developer_from_jira_json(assignee_json)
            assignee_id = find_developer_id_by_email(new_conn, assignee_email)

            if assignee_id:
                status_changed_dt = parse_jira_date_to_local(status_changed, tz)
                if status_changed_dt:
                    event_date = status_changed_dt.date()
                    event_hour = status_changed_dt.hour
                    time_bucket = get_time_bucket(status_changed_dt)
                    sprint_id = find_sprint_for_date(event_date, sprint_date_map)

                    new_cursor.execute(
                        """
                        INSERT INTO jira_events (
                            developer_id, event_type, event_timestamp, event_date,
                            event_hour, time_bucket, issue_id, sprint_id
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            assignee_id,
                            "status_changed",
                            status_changed,
                            event_date.isoformat(),
                            event_hour,
                            time_bucket,
                            issue_id,
                            sprint_id,
                        ),
                    )
                    count += 1

    new_conn.commit()
    console.print(f"[bold green]✓ Extracted {count} Jira events[/bold green]")

    return count
