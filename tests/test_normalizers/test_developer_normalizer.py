"""Tests for developer normalization and merging."""

import sqlite3
import pytest
from sdm_tools.database.normalizers.developer_normalizer import (
    merge_developer_data,
    populate_developers_table,
    find_developer_id_by_email
)
from sdm_tools.database.schema import create_normalized_schema


@pytest.fixture
def in_memory_db():
    """Create an in-memory database with schema."""
    conn = sqlite3.connect(':memory:')
    create_normalized_schema(conn)
    yield conn
    conn.close()


class TestMergeDeveloperData:
    """Test merging of Jira and Git developer data."""
    
    def test_merge_jira_only_developer(self):
        """Test developer exists only in Jira."""
        jira_devs = {
            'john.doe@example.com': {
                'name': 'John Doe',
                'account_id': 'acc-123',
                'aliases': set()
            }
        }
        git_emails = {}
        
        result = merge_developer_data(jira_devs, git_emails)
        
        assert 'john.doe@example.com' in result
        assert result['john.doe@example.com']['name'] == 'John Doe'
        assert result['john.doe@example.com']['account_id'] == 'acc-123'
    
    def test_merge_git_only_developer(self):
        """Test developer exists only in Git."""
        jira_devs = {}
        git_emails = {
            'jane.smith@example.com': ['jane.smith@example.com', 'jsmith@example.com']
        }
        
        result = merge_developer_data(jira_devs, git_emails)
        
        assert 'jane.smith@example.com' in result
        # Name should be derived from email
        assert 'Jane Smith' in result['jane.smith@example.com']['name']
        assert result['jane.smith@example.com']['account_id'] == ''
        # Aliases should include git variations
        assert 'jsmith@example.com' in result['jane.smith@example.com']['aliases']
    
    def test_merge_developer_in_both_systems(self):
        """Test developer exists in both Jira and Git."""
        jira_devs = {
            'john.doe@example.com': {
                'name': 'John Doe',
                'account_id': 'acc-123',
                'aliases': set()
            }
        }
        git_emails = {
            'john.doe@example.com': ['john.doe@example.com', 'jdoe@example.com', 'john@example.com']
        }
        
        result = merge_developer_data(jira_devs, git_emails)
        
        assert 'john.doe@example.com' in result
        # Should keep Jira name and account_id
        assert result['john.doe@example.com']['name'] == 'John Doe'
        assert result['john.doe@example.com']['account_id'] == 'acc-123'
        # Should add git aliases
        assert 'jdoe@example.com' in result['john.doe@example.com']['aliases']
        assert 'john@example.com' in result['john.doe@example.com']['aliases']
    
    def test_merge_multiple_developers(self):
        """Test merging multiple developers from both systems."""
        jira_devs = {
            'john@example.com': {'name': 'John', 'account_id': 'acc-1', 'aliases': set()},
            'jane@example.com': {'name': 'Jane', 'account_id': 'acc-2', 'aliases': set()}
        }
        git_emails = {
            'jane@example.com': ['jane@example.com', 'jsmith@example.com'],
            'bob@example.com': ['bob@example.com']
        }
        
        result = merge_developer_data(jira_devs, git_emails)
        
        # Should have all 3 developers
        assert len(result) == 3
        assert 'john@example.com' in result
        assert 'jane@example.com' in result
        assert 'bob@example.com' in result
        
        # Jane should have git aliases added
        assert 'jsmith@example.com' in result['jane@example.com']['aliases']


class TestPopulateDevelopersTable:
    """Test populating developers table in database."""
    
    def test_populate_single_developer(self, in_memory_db):
        """Test inserting a single developer."""
        developers_data = {
            'test@example.com': {
                'name': 'Test User',
                'account_id': 'acc-123',
                'aliases': set()
            }
        }
        
        email_to_id = populate_developers_table(in_memory_db, developers_data)
        
        assert 'test@example.com' in email_to_id
        
        # Verify data in database
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT email, name, jira_account_id FROM developers WHERE email = ?", 
                      ('test@example.com',))
        row = cursor.fetchone()
        
        assert row[0] == 'test@example.com'
        assert row[1] == 'Test User'
        assert row[2] == 'acc-123'
    
    def test_populate_developer_with_aliases(self, in_memory_db):
        """Test inserting developer with email aliases."""
        developers_data = {
            'john@example.com': {
                'name': 'John Doe',
                'account_id': 'acc-456',
                'aliases': {'jdoe@example.com', 'john.doe@example.com'}
            }
        }
        
        email_to_id = populate_developers_table(in_memory_db, developers_data)
        dev_id = email_to_id['john@example.com']
        
        # Verify aliases in database
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT alias_email FROM developer_email_aliases WHERE developer_id = ?", 
                      (dev_id,))
        aliases = [row[0] for row in cursor.fetchall()]
        
        assert 'jdoe@example.com' in aliases
        assert 'john.doe@example.com' in aliases
        # Primary email should NOT be in aliases table
        assert 'john@example.com' not in aliases
    
    def test_populate_multiple_developers(self, in_memory_db):
        """Test inserting multiple developers."""
        developers_data = {
            'dev1@example.com': {'name': 'Dev One', 'account_id': 'acc-1', 'aliases': set()},
            'dev2@example.com': {'name': 'Dev Two', 'account_id': 'acc-2', 'aliases': set()},
            'dev3@example.com': {'name': 'Dev Three', 'account_id': 'acc-3', 'aliases': set()}
        }
        
        email_to_id = populate_developers_table(in_memory_db, developers_data)
        
        assert len(email_to_id) == 3
        
        # Verify all in database
        cursor = in_memory_db.cursor()
        cursor.execute("SELECT COUNT(*) FROM developers")
        count = cursor.fetchone()[0]
        
        assert count == 3


class TestFindDeveloperIdByEmail:
    """Test finding developer by email with alias matching."""
    
    def test_find_by_primary_email(self, in_memory_db):
        """Test finding developer by primary email."""
        # Insert a developer
        cursor = in_memory_db.cursor()
        cursor.execute("""
            INSERT INTO developers (email, name, jira_account_id, active)
            VALUES ('john@example.com', 'John Doe', 'acc-123', 1)
        """)
        dev_id = cursor.lastrowid
        in_memory_db.commit()
        
        # Find by primary email
        found_id = find_developer_id_by_email(in_memory_db, 'john@example.com')
        
        assert found_id == dev_id
    
    def test_find_by_alias_email(self, in_memory_db):
        """Test finding developer by alias email."""
        # Insert developer
        cursor = in_memory_db.cursor()
        cursor.execute("""
            INSERT INTO developers (email, name, jira_account_id, active)
            VALUES ('john@example.com', 'John Doe', 'acc-123', 1)
        """)
        dev_id = cursor.lastrowid
        
        # Insert alias
        cursor.execute("""
            INSERT INTO developer_email_aliases (developer_id, alias_email, source)
            VALUES (?, 'jdoe@example.com', 'git')
        """, (dev_id,))
        in_memory_db.commit()
        
        # Find by alias
        found_id = find_developer_id_by_email(in_memory_db, 'jdoe@example.com')
        
        assert found_id == dev_id
    
    def test_find_by_unnormalized_email(self, in_memory_db):
        """Test finding developer with email normalization."""
        # Insert developer with normalized email
        cursor = in_memory_db.cursor()
        cursor.execute("""
            INSERT INTO developers (email, name, jira_account_id, active)
            VALUES ('john@example.com', 'John Doe', 'acc-123', 1)
        """)
        dev_id = cursor.lastrowid
        in_memory_db.commit()
        
        # Find with uppercase (should normalize and match)
        found_id = find_developer_id_by_email(in_memory_db, 'JOHN@EXAMPLE.COM')
        
        assert found_id == dev_id
    
    def test_find_nonexistent_email(self, in_memory_db):
        """Test finding developer that doesn't exist."""
        found_id = find_developer_id_by_email(in_memory_db, 'notfound@example.com')
        
        assert found_id is None
    
    def test_find_none_email(self, in_memory_db):
        """Test finding with None email."""
        found_id = find_developer_id_by_email(in_memory_db, None)
        
        assert found_id is None
    
    def test_find_empty_email(self, in_memory_db):
        """Test finding with empty email."""
        found_id = find_developer_id_by_email(in_memory_db, '')
        
        assert found_id is None
    
    def test_find_with_aws_sso_prefix(self, in_memory_db):
        """Test finding developer when search email has AWS SSO prefix."""
        # Insert developer with normalized email
        cursor = in_memory_db.cursor()
        cursor.execute("""
            INSERT INTO developers (email, name, jira_account_id, active)
            VALUES ('john@telus.com', 'John Doe', 'acc-123', 1)
        """)
        dev_id = cursor.lastrowid
        in_memory_db.commit()
        
        # Search with AWS SSO prefix - should normalize and match
        found_id = find_developer_id_by_email(in_memory_db, 
                                             'AWSReservedSSO_Role/john@telusinternational.com')
        
        assert found_id == dev_id
