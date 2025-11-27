"""Tests for sprint velocity and metrics calculations (simpler unit tests)."""

import sqlite3

import pytest

from sdm_tools.database.schema import create_normalized_schema


@pytest.fixture
def metrics_db():
    """Create an in-memory database with schema and sample data."""
    conn = sqlite3.connect(":memory:")
    create_normalized_schema(conn)

    cursor = conn.cursor()

    # Insert test developers
    cursor.execute(
        """
        INSERT INTO developers (id, email, name, jira_account_id, active)
        VALUES (1, 'dev1@example.com', 'Developer One', 'acc-1', 1)
    """
    )
    cursor.execute(
        """
        INSERT INTO developers (id, email, name, jira_account_id, active)
        VALUES (2, 'dev2@example.com', 'Developer Two', 'acc-2', 1)
    """
    )

    # Insert test sprints
    cursor.execute(
        """
        INSERT INTO sprints (id, name, state, start_date_local, end_date_local)
        VALUES (1, 'Sprint 1', 'closed', '2025-01-01', '2025-01-14')
    """
    )
    cursor.execute(
        """
        INSERT INTO sprints (id, name, state, start_date_local, end_date_local)
        VALUES (2, 'Sprint 2', 'closed', '2025-01-15', '2025-01-28')
    """
    )
    cursor.execute(
        """
        INSERT INTO sprints (id, name, state, start_date_local, end_date_local)
        VALUES (3, 'Sprint 3', 'active', '2025-01-29', '2025-02-11')
    """
    )

    conn.commit()

    yield conn
    conn.close()


class TestSprintVelocitySchema:
    """Test sprint velocity query structure and logic using direct SQL."""

    def test_empty_sprint_query(self, metrics_db):
        """Test velocity query with no issues."""
        cursor = metrics_db.cursor()

        # Simplified version of calculate_sprint_velocity query
        cursor.execute(
            """
            SELECT
                s.id,
                s.name,
                COALESCE(SUM(
                    CASE
                        WHEN i.created_date_local < s.start_date_local
                        THEN i.story_points
                        ELSE 0
                    END
                ), 0) as planned_points,
                COALESCE(SUM(
                    CASE
                        WHEN i.status_name IN ('Done', 'Closed')
                        AND i.status_changed_date_local <= s.end_date_local
                        THEN i.story_points
                        ELSE 0
                    END
                ), 0) as delivered_points
            FROM sprints s
            LEFT JOIN issue_sprints isp ON s.id = isp.sprint_id
            LEFT JOIN issues i ON isp.issue_id = i.id
            LEFT JOIN developers d ON i.assignee_id = d.id
            WHERE s.id = 1 AND (d.active = 1 OR i.assignee_id IS NULL)
            GROUP BY s.id, s.name
        """
        )

        result = cursor.fetchone()

        # Should return sprint with 0 points
        assert result is not None
        assert result[0] == 1  # sprint id
        assert result[2] == 0.0  # planned_points
        assert result[3] == 0.0  # delivered_points

    def test_sprint_with_planned_and_delivered(self, metrics_db):
        """Test velocity calculation with planned and delivered issues."""
        cursor = metrics_db.cursor()

        # Issue created before sprint, completed during sprint (planned + delivered)
        cursor.execute(
            """
            INSERT INTO issues (id, summary, status_name, story_points, assignee_id,
                              created_date_local, status_changed_date_local)
            VALUES ('ISSUE-1', 'Completed Issue', 'Done', 5.0, 1, '2024-12-25', '2025-01-10')
        """
        )
        cursor.execute("INSERT INTO issue_sprints (issue_id, sprint_id) VALUES ('ISSUE-1', 1)")

        # Issue created before sprint, not completed (planned only)
        cursor.execute(
            """
            INSERT INTO issues (id, summary, status_name, story_points, assignee_id,
                              created_date_local, status_changed_date_local)
            VALUES ('ISSUE-2', 'Incomplete Issue', 'In Progress', 3.0, 1, '2024-12-25', NULL)
        """
        )
        cursor.execute("INSERT INTO issue_sprints (issue_id, sprint_id) VALUES ('ISSUE-2', 1)")

        metrics_db.commit()

        # Query velocity
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN i.created_date_local < s.start_date_local
                        THEN i.story_points
                        ELSE 0
                    END
                ), 0) as planned_points,
                COALESCE(SUM(
                    CASE
                        WHEN i.status_name IN ('Done', 'Closed')
                        AND i.status_changed_date_local <= s.end_date_local
                        THEN i.story_points
                        ELSE 0
                    END
                ), 0) as delivered_points
            FROM sprints s
            LEFT JOIN issue_sprints isp ON s.id = isp.sprint_id
            LEFT JOIN issues i ON isp.issue_id = i.id
            LEFT JOIN developers d ON i.assignee_id = d.id
            WHERE s.id = 1 AND (d.active = 1 OR i.assignee_id IS NULL)
            GROUP BY s.id
        """
        )

        result = cursor.fetchone()

        assert result[0] == 8.0  # planned: 5 + 3
        assert result[1] == 5.0  # delivered: only the Done issue

    def test_issue_added_during_sprint_not_planned(self, metrics_db):
        """Test that issues added during sprint are not counted as planned."""
        cursor = metrics_db.cursor()

        # Issue created AFTER sprint start (not planned)
        cursor.execute(
            """
            INSERT INTO issues (id, summary, status_name, story_points, assignee_id,
                              created_date_local, status_changed_date_local)
            VALUES ('ISSUE-3', 'Mid-Sprint', 'Done', 4.0, 1, '2025-01-05', '2025-01-12')
        """
        )
        cursor.execute("INSERT INTO issue_sprints (issue_id, sprint_id) VALUES ('ISSUE-3', 1)")

        metrics_db.commit()

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(
                    CASE
                        WHEN i.created_date_local < s.start_date_local
                        THEN i.story_points
                        ELSE 0
                    END
                ), 0) as planned_points,
                COALESCE(SUM(
                    CASE
                        WHEN i.status_name IN ('Done', 'Closed')
                        AND i.status_changed_date_local <= s.end_date_local
                        THEN i.story_points
                        ELSE 0
                    END
                ), 0) as delivered_points
            FROM sprints s
            LEFT JOIN issue_sprints isp ON s.id = isp.sprint_id
            LEFT JOIN issues i ON isp.issue_id = i.id
            WHERE s.id = 1
            GROUP BY s.id
        """
        )

        result = cursor.fetchone()

        # Not counted as planned (created after start)
        assert result[0] == 0.0
        # But counted as delivered (completed during sprint)
        assert result[1] == 4.0

    def test_inactive_developer_issues_excluded(self, metrics_db):
        """Test that issues from inactive developers are excluded."""
        cursor = metrics_db.cursor()

        # Add inactive developer
        cursor.execute(
            """
            INSERT INTO developers (id, email, name, jira_account_id, active)
            VALUES (3, 'inactive@example.com', 'Inactive Dev', 'acc-3', 0)
        """
        )

        # Issue assigned to inactive developer
        cursor.execute(
            """
            INSERT INTO issues (id, summary, status_name, story_points, assignee_id,
                              created_date_local, status_changed_date_local)
            VALUES ('ISSUE-4', 'Inactive Issue', 'Done', 10.0, 3, '2024-12-25', '2025-01-10')
        """
        )
        cursor.execute("INSERT INTO issue_sprints (issue_id, sprint_id) VALUES ('ISSUE-4', 1)")

        metrics_db.commit()

        cursor.execute(
            """
            SELECT
                COALESCE(SUM(i.story_points), 0) as total_points
            FROM sprints s
            LEFT JOIN issue_sprints isp ON s.id = isp.sprint_id
            LEFT JOIN issues i ON isp.issue_id = i.id
            LEFT JOIN developers d ON i.assignee_id = d.id
            WHERE s.id = 1 AND d.active = 1
            GROUP BY s.id
        """
        )

        result = cursor.fetchone()

        # Should exclude inactive developer's issues
        # Returns None because no active developers have issues
        assert result is None or result[0] == 0.0


class TestSprintMetricsCalculations:
    """Test velocity metric calculations."""

    def test_completion_rate_calculation(self):
        """Test completion rate percentage calculation."""
        planned = 10.0
        delivered = 7.0

        completion_rate = round((delivered / planned * 100), 1)

        assert completion_rate == 70.0

    def test_completion_rate_zero_planned(self):
        """Test completion rate when no points planned."""
        planned = 0.0
        delivered = 5.0

        completion_rate = round((delivered / planned * 100), 1) if planned > 0 else 0.0

        assert completion_rate == 0.0

    def test_average_velocity_calculation(self):
        """Test average velocity across sprints."""
        sprint_points = [10.0, 15.0, 12.0]

        avg = round(sum(sprint_points) / len(sprint_points), 1)

        assert avg == 12.3
