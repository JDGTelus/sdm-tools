"""Tests for database schema creation and structure."""

import sqlite3

import pytest

from sdm_tools.database.schema import create_normalized_schema, get_table_stats


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database for testing."""
    conn = sqlite3.connect(":memory:")
    yield conn
    conn.close()


class TestSchemaCreation:
    """Test database schema creation."""

    def test_create_all_tables(self, in_memory_db):
        """Test that all 8 tables are created."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall() if row[0] != "sqlite_sequence"]

        expected_tables = [
            "daily_activity_summary",
            "developer_email_aliases",
            "developers",
            "git_events",
            "issue_sprints",
            "issues",
            "jira_events",
            "sprints",
        ]

        assert sorted(tables) == sorted(expected_tables)

    def test_developers_table_structure(self, in_memory_db):
        """Test developers table has correct columns."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA table_info(developers)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}  # {name: type}

        assert "id" in columns
        assert "email" in columns
        assert "name" in columns
        assert "jira_account_id" in columns
        assert "active" in columns
        assert "created_at" in columns

    def test_developer_email_aliases_table_structure(self, in_memory_db):
        """Test developer_email_aliases table has correct columns."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA table_info(developer_email_aliases)")
        columns = [row[1] for row in cursor.fetchall()]

        assert "developer_id" in columns
        assert "alias_email" in columns
        assert "source" in columns

    def test_sprints_table_structure(self, in_memory_db):
        """Test sprints table has correct columns."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA table_info(sprints)")
        columns = [row[1] for row in cursor.fetchall()]

        assert "id" in columns
        assert "name" in columns
        assert "state" in columns
        assert "start_date" in columns
        assert "end_date" in columns
        assert "start_date_local" in columns
        assert "end_date_local" in columns

    def test_issues_table_structure(self, in_memory_db):
        """Test issues table has correct columns."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA table_info(issues)")
        columns = [row[1] for row in cursor.fetchall()]

        assert "id" in columns
        assert "summary" in columns
        assert "status_name" in columns
        assert "story_points" in columns
        assert "assignee_id" in columns
        assert "creator_id" in columns
        assert "created_at" in columns
        assert "updated_at" in columns

    def test_jira_events_table_structure(self, in_memory_db):
        """Test jira_events table has correct columns."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA table_info(jira_events)")
        columns = [row[1] for row in cursor.fetchall()]

        assert "id" in columns
        assert "developer_id" in columns
        assert "event_type" in columns
        assert "event_timestamp" in columns
        assert "event_date" in columns
        assert "event_hour" in columns
        assert "time_bucket" in columns
        assert "issue_id" in columns
        assert "sprint_id" in columns

    def test_git_events_table_structure(self, in_memory_db):
        """Test git_events table has correct columns."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA table_info(git_events)")
        columns = [row[1] for row in cursor.fetchall()]

        assert "id" in columns
        assert "developer_id" in columns
        assert "commit_hash" in columns
        assert "commit_timestamp" in columns
        assert "commit_date" in columns
        assert "commit_hour" in columns
        assert "time_bucket" in columns
        assert "sprint_id" in columns
        assert "message" in columns

    def test_daily_activity_summary_table_structure(self, in_memory_db):
        """Test daily_activity_summary table has correct columns."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA table_info(daily_activity_summary)")
        columns = [row[1] for row in cursor.fetchall()]

        assert "id" in columns
        assert "activity_date" in columns
        assert "developer_id" in columns
        assert "sprint_id" in columns
        assert "time_bucket" in columns
        assert "jira_count" in columns
        assert "git_count" in columns
        assert "total_count" in columns


class TestIndexes:
    """Test database indexes are created."""

    def test_developer_indexes_created(self, in_memory_db):
        """Test developers table has required indexes."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='developers'"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        # Should have indexes on email and active
        assert any("email" in idx for idx in indexes)
        assert any("active" in idx for idx in indexes)

    def test_jira_events_indexes_created(self, in_memory_db):
        """Test jira_events table has required indexes."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='jira_events'"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        # Should have indexes on developer_id/date, sprint_id, and date
        assert len(indexes) >= 2  # At least some indexes created

    def test_git_events_indexes_created(self, in_memory_db):
        """Test git_events table has required indexes."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='git_events'"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        assert len(indexes) >= 2

    def test_daily_activity_summary_indexes_created(self, in_memory_db):
        """Test daily_activity_summary table has required indexes."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='daily_activity_summary'"
        )
        indexes = [row[0] for row in cursor.fetchall()]

        # Should have indexes on date, sprint_id, and developer_id/date
        assert len(indexes) >= 2


class TestForeignKeys:
    """Test foreign key relationships."""

    def test_issue_sprints_foreign_keys(self, in_memory_db):
        """Test issue_sprints has foreign key relationships."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA foreign_key_list(issue_sprints)")
        fks = cursor.fetchall()

        # Should have 2 foreign keys (issue_id -> issues, sprint_id -> sprints)
        assert len(fks) == 2

    def test_developer_email_aliases_foreign_keys(self, in_memory_db):
        """Test developer_email_aliases has foreign key to developers."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()
        cursor.execute("PRAGMA foreign_key_list(developer_email_aliases)")
        fks = cursor.fetchall()

        # Should have 1 foreign key (developer_id -> developers)
        assert len(fks) == 1


class TestGetTableStats:
    """Test table statistics function."""

    def test_get_stats_empty_database(self, in_memory_db):
        """Test stats for newly created empty database."""
        create_normalized_schema(in_memory_db)

        stats = get_table_stats(in_memory_db)

        # All tables should exist with 0 rows
        assert stats["developers"] == 0
        assert stats["sprints"] == 0
        assert stats["issues"] == 0
        assert stats["jira_events"] == 0
        assert stats["git_events"] == 0
        assert stats["daily_activity_summary"] == 0

    def test_get_stats_with_data(self, in_memory_db):
        """Test stats after inserting some data."""
        create_normalized_schema(in_memory_db)

        cursor = in_memory_db.cursor()

        # Insert a test developer
        cursor.execute(
            """
            INSERT INTO developers (email, name, jira_account_id, active)
            VALUES ('test@example.com', 'Test User', 'acc-123', 1)
        """
        )

        # Insert a test sprint
        cursor.execute(
            """
            INSERT INTO sprints (id, name, state, start_date_local, end_date_local)
            VALUES (1, 'Sprint 1', 'closed', '2025-01-01', '2025-01-15')
        """
        )

        in_memory_db.commit()

        stats = get_table_stats(in_memory_db)

        assert stats["developers"] == 1
        assert stats["sprints"] == 1
        assert stats["issues"] == 0
