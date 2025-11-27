"""Data ingestion with upsert logic for incremental updates."""

import json

from rich.console import Console

from .simple_utils import (
    create_metadata_json,
    find_sprint_for_date,
    get_local_date,
    is_developer_active,
    normalize_email,
)

console = Console()


def upsert_developer(conn, email, name):
    """Insert or update developer record.

    Args:
        conn: SQLite connection
        email: Developer email (will be normalized)
        name: Developer name

    Returns:
        Normalized email (used as PK)
    """
    normalized_email = normalize_email(email)
    if not normalized_email:
        return None

    cursor = conn.cursor()
    active = is_developer_active(normalized_email)

    cursor.execute(
        """
        INSERT INTO developers (email, name, active, last_seen)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(email) DO UPDATE SET
            name = excluded.name,
            active = excluded.active,
            last_seen = CURRENT_TIMESTAMP
    """,
        (normalized_email, name, active),
    )

    return normalized_email


def get_all_sprints(conn):
    """Get all sprints from database for date matching.

    Args:
        conn: SQLite connection

    Returns:
        List of sprint dicts
    """
    cursor = conn.cursor()
    cursor.execute("SELECT name, start_date, end_date FROM sprints")
    rows = cursor.fetchall()

    return [{"name": row[0], "start_date": row[1], "end_date": row[2]} for row in rows]


def ingest_jira_issue(conn, issue_data):
    """Ingest a single Jira issue and create activity events.

    Args:
        conn: SQLite connection
        issue_data: Raw Jira issue dict from API

    Returns:
        Number of events created
    """
    cursor = conn.cursor()
    events_created = 0

    try:
        fields = issue_data.get("fields", {})
        issue_key = issue_data.get("key")

        # Extract sprint info
        sprint_name = None
        sprint_field = fields.get("customfield_10020")  # Standard sprint field
        if sprint_field and isinstance(sprint_field, list) and len(sprint_field) > 0:
            sprint_obj = sprint_field[-1]  # Most recent sprint
            if isinstance(sprint_obj, dict):
                sprint_name = sprint_obj.get("name")

        # Get all sprints for date-based matching
        all_sprints = get_all_sprints(conn)

        # 1. Issue Created Event
        created_at = fields.get("created")
        creator = fields.get("creator", {})
        creator_email = creator.get("emailAddress")
        creator_name = creator.get("displayName", "Unknown")

        if created_at and creator_email:
            dev_email = upsert_developer(conn, creator_email, creator_name)
            if dev_email:
                event_date = get_local_date(created_at)
                if not sprint_name and event_date:
                    sprint_name = find_sprint_for_date(event_date, all_sprints)

                metadata = create_metadata_json(
                    issue_key=issue_key,
                    summary=fields.get("summary"),
                    issue_type=fields.get("issuetype", {}).get("name"),
                )

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO activity_events
                    (developer_email, event_type, event_timestamp, event_date,
                     sprint_name, issue_key, metadata)
                    VALUES (?, 'jira_create', ?, ?, ?, ?, ?)
                """,
                    (dev_email, created_at, event_date, sprint_name, issue_key, metadata),
                )

                if cursor.rowcount > 0:
                    events_created += 1

        # 2. Issue Updated Event
        updated_at = fields.get("updated")
        assignee = fields.get("assignee", {})
        assignee_email = assignee.get("emailAddress")
        assignee_name = assignee.get("displayName", "Unknown")

        if updated_at and assignee_email and updated_at != created_at:
            dev_email = upsert_developer(conn, assignee_email, assignee_name)
            if dev_email:
                event_date = get_local_date(updated_at)
                if not sprint_name and event_date:
                    sprint_name = find_sprint_for_date(event_date, all_sprints)

                metadata = create_metadata_json(
                    issue_key=issue_key,
                    summary=fields.get("summary"),
                    status=fields.get("status", {}).get("name"),
                    story_points=fields.get("customfield_10016"),  # Story points
                )

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO activity_events
                    (developer_email, event_type, event_timestamp, event_date,
                     sprint_name, issue_key, metadata)
                    VALUES (?, 'jira_update', ?, ?, ?, ?, ?)
                """,
                    (dev_email, updated_at, event_date, sprint_name, issue_key, metadata),
                )

                if cursor.rowcount > 0:
                    events_created += 1

        # 3. Store sprint info
        if sprint_name and sprint_field:
            sprint_obj = sprint_field[-1]
            if isinstance(sprint_obj, dict):
                upsert_sprint(
                    conn,
                    name=sprint_name,
                    state=sprint_obj.get("state"),
                    start_date=sprint_obj.get("startDate"),
                    end_date=sprint_obj.get("endDate"),
                    jira_id=sprint_obj.get("id"),
                )

        return events_created

    except Exception as e:
        console.print(
            f"[yellow]Warning: Error ingesting issue {issue_data.get('key')}: {e}[/yellow]"
        )
        return 0


def ingest_git_commit(conn, commit_data):
    """Ingest a single git commit as an activity event.

    Args:
        conn: SQLite connection
        commit_data: Dict with commit info (hash, author, email, timestamp, message)

    Returns:
        True if event was created, False if skipped (duplicate)
    """
    cursor = conn.cursor()

    try:
        commit_hash = commit_data.get("hash")
        author_email = commit_data.get("email")
        author_name = commit_data.get("author", "Unknown")
        timestamp = commit_data.get("timestamp")
        message = commit_data.get("message", "")

        if not commit_hash or not author_email or not timestamp:
            return False

        # Upsert developer
        dev_email = upsert_developer(conn, author_email, author_name)
        if not dev_email:
            return False

        # Get date and sprint
        event_date = get_local_date(timestamp)
        all_sprints = get_all_sprints(conn)
        sprint_name = find_sprint_for_date(event_date, all_sprints) if event_date else None

        # Create metadata
        metadata = create_metadata_json(message=message[:500])  # Truncate long messages

        # Insert event (unique constraint on commit_hash prevents duplicates)
        cursor.execute(
            """
            INSERT OR IGNORE INTO activity_events
            (developer_email, event_type, event_timestamp, event_date,
             sprint_name, commit_hash, metadata)
            VALUES (?, 'commit', ?, ?, ?, ?, ?)
        """,
            (dev_email, timestamp, event_date, sprint_name, commit_hash, metadata),
        )

        return cursor.rowcount > 0

    except Exception as e:
        console.print(
            f"[yellow]Warning: Error ingesting commit {commit_data.get('hash')}: {e}[/yellow]"
        )
        return False


def upsert_sprint(conn, name, state=None, start_date=None, end_date=None, jira_id=None):
    """Insert or update sprint record.

    Args:
        conn: SQLite connection
        name: Sprint name (PK)
        state: Sprint state (active, closed, future)
        start_date: Start date (ISO format or date string)
        end_date: End date (ISO format or date string)
        jira_id: Jira sprint ID
    """
    cursor = conn.cursor()

    # Parse dates if needed
    if start_date and "T" in start_date:
        start_date = get_local_date(start_date)
    if end_date and "T" in end_date:
        end_date = get_local_date(end_date)

    cursor.execute(
        """
        INSERT INTO sprints (name, state, start_date, end_date, jira_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(name) DO UPDATE SET
            state = COALESCE(excluded.state, state),
            start_date = COALESCE(excluded.start_date, start_date),
            end_date = COALESCE(excluded.end_date, end_date),
            jira_id = COALESCE(excluded.jira_id, jira_id)
    """,
        (name, state, start_date, end_date, jira_id),
    )


def calculate_sprint_points(conn):
    """Calculate planned vs delivered points for all sprints.

    Updates sprints table with aggregated story points.

    Args:
        conn: SQLite connection
    """
    cursor = conn.cursor()

    # Get all sprints
    cursor.execute("SELECT name FROM sprints")
    sprints = [row[0] for row in cursor.fetchall()]

    for sprint_name in sprints:
        # Get all issues in this sprint
        cursor.execute(
            """
            SELECT DISTINCT issue_key, metadata
            FROM activity_events
            WHERE sprint_name = ?
              AND issue_key IS NOT NULL
        """,
            (sprint_name,),
        )

        total_planned = 0
        total_delivered = 0

        for _issue_key, metadata_json in cursor.fetchall():
            if not metadata_json:
                continue

            try:
                metadata = json.loads(metadata_json)
                story_points = metadata.get("story_points")
                status = metadata.get("status", "").lower()

                if story_points and isinstance(story_points, (int, float)):
                    total_planned += story_points

                    # Consider done/closed as delivered
                    if any(word in status for word in ["done", "closed", "complete"]):
                        total_delivered += story_points
            except:
                continue

        # Update sprint
        cursor.execute(
            """
            UPDATE sprints
            SET total_planned_points = ?,
                total_delivered_points = ?
            WHERE name = ?
        """,
            (total_planned, total_delivered, sprint_name),
        )

    conn.commit()


def get_last_jira_sync_time(conn):
    """Get timestamp of most recent Jira event.

    Args:
        conn: SQLite connection

    Returns:
        ISO timestamp string or None
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT MAX(event_timestamp)
        FROM activity_events
        WHERE event_type LIKE 'jira_%'
    """
    )
    result = cursor.fetchone()
    return result[0] if result and result[0] else None


def get_last_commit_hash(conn):
    """Get hash of most recent commit.

    Args:
        conn: SQLite connection

    Returns:
        Commit hash string or None
    """
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT commit_hash
        FROM activity_events
        WHERE event_type = 'commit'
        ORDER BY event_timestamp DESC
        LIMIT 1
    """
    )
    result = cursor.fetchone()
    return result[0] if result and result[0] else None
