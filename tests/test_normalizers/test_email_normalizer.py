"""Tests for email normalization functionality."""

from sdm_tools.database.normalizers.email_normalizer import (
    extract_developer_from_jira_json,
    normalize_email,
)


class TestNormalizeEmail:
    """Test email normalization with various edge cases."""

    def test_basic_lowercase(self):
        """Test basic case normalization."""
        assert normalize_email("User@Domain.COM") == "user@domain.com"
        assert normalize_email("ADMIN@EXAMPLE.COM") == "admin@example.com"

    def test_whitespace_stripping(self):
        """Test whitespace removal."""
        assert normalize_email("  user@domain.com  ") == "user@domain.com"
        assert normalize_email("\tuser@domain.com\n") == "user@domain.com"

    def test_aws_sso_prefix_removal(self):
        """Test AWS SSO prefix patterns."""
        # Standard AWS SSO pattern
        assert (
            normalize_email("AWSReservedSSO_TELUS-IoT-Developer_xxx/user@telus.com")
            == "user@telus.com"
        )

        # Different SSO variations
        assert (
            normalize_email("AWSReservedSSO_SomeRole/john.doe@example.com")
            == "john.doe@example.com"
        )
        assert (
            normalize_email("AWSReservedSSO_Admin_12345/admin@company.com") == "admin@company.com"
        )

    def test_domain_normalization(self):
        """Test domain variation mapping."""
        # telusinternational.com -> telus.com
        assert normalize_email("user@telusinternational.com") == "user@telus.com"
        assert normalize_email("admin@TELUSINTERNATIONAL.COM") == "admin@telus.com"

        # Other domains should remain unchanged
        assert normalize_email("user@gmail.com") == "user@gmail.com"
        assert normalize_email("test@example.org") == "test@example.org"

    def test_numeric_suffix_removal(self):
        """Test removal of numeric suffixes from local part."""
        # Single digits
        assert normalize_email("carlos.carias01@telus.com") == "carlos.carias@telus.com"
        assert normalize_email("john.doe1@example.com") == "john.doe@example.com"

        # Multiple digits
        assert normalize_email("user123@domain.com") == "user@domain.com"
        assert normalize_email("admin999@company.com") == "admin@company.com"

        # No numeric suffix - should remain unchanged
        assert normalize_email("john.doe@example.com") == "john.doe@example.com"

    def test_combined_transformations(self):
        """Test multiple transformations together."""
        # AWS SSO + domain normalization + case + numeric suffix
        email = "AWSReservedSSO_Role/Carlos.Carias01@TELUSINTERNATIONAL.COM"
        expected = "carlos.carias@telus.com"
        assert normalize_email(email) == expected

        # Whitespace + AWS SSO + lowercase
        email = "  AWSReservedSSO_Dev/User@Example.COM  "
        expected = "user@example.com"
        assert normalize_email(email) == expected

    def test_none_and_empty_inputs(self):
        """Test handling of None and empty strings."""
        assert normalize_email(None) is None
        assert normalize_email("") is None
        # Whitespace-only strings return empty string after strip
        assert normalize_email("   ") == ""

    def test_unknown_email(self):
        """Test handling of 'Unknown' placeholder."""
        assert normalize_email("Unknown") is None
        # Lowercase 'unknown' is not special - becomes normalized
        # The function only checks for exact 'Unknown' before case conversion

    def test_malformed_emails(self):
        """Test edge cases with unusual formats."""
        # Missing @ symbol - should still process
        # (normalize_email doesn't validate, just transforms)
        assert normalize_email("notanemail") == "notanemail"

        # Multiple @ symbols - should still process
        assert normalize_email("user@@domain.com") == "user@@domain.com"


class TestExtractDeveloperFromJiraJson:
    """Test Jira JSON developer extraction."""

    def test_valid_jira_json(self):
        """Test extraction from valid Jira assignee/creator JSON."""
        jira_json = "{'emailAddress': 'john.doe@example.com', 'displayName': 'John Doe', 'accountId': 'acc-123'}"
        email, name, account_id = extract_developer_from_jira_json(jira_json)

        assert email == "john.doe@example.com"
        assert name == "John Doe"
        assert account_id == "acc-123"

    def test_jira_json_with_aws_sso(self):
        """Test extraction with AWS SSO email."""
        jira_json = "{'emailAddress': 'AWSReservedSSO_Role/user@telusinternational.com', 'displayName': 'Test User', 'accountId': 'acc-456'}"
        email, name, account_id = extract_developer_from_jira_json(jira_json)

        # Should normalize the email
        assert email == "user@telus.com"
        assert name == "Test User"
        assert account_id == "acc-456"

    def test_jira_json_missing_fields(self):
        """Test extraction with missing fields."""
        # Missing emailAddress
        jira_json = "{'displayName': 'John Doe', 'accountId': 'acc-123'}"
        email, name, account_id = extract_developer_from_jira_json(jira_json)

        assert email is None  # No email in dict, normalize_email('') returns None
        assert name == "John Doe"
        assert account_id == "acc-123"

    def test_jira_json_empty_values(self):
        """Test extraction with empty values."""
        jira_json = "{'emailAddress': '', 'displayName': '', 'accountId': ''}"
        email, name, account_id = extract_developer_from_jira_json(jira_json)

        assert email is None
        assert name == ""
        assert account_id == ""

    def test_none_input(self):
        """Test handling of None input."""
        email, name, account_id = extract_developer_from_jira_json(None)

        assert email is None
        assert name is None
        assert account_id is None

    def test_empty_string_input(self):
        """Test handling of empty string."""
        email, name, account_id = extract_developer_from_jira_json("")

        assert email is None
        assert name is None
        assert account_id is None

    def test_malformed_json(self):
        """Test handling of malformed JSON string."""
        # Invalid JSON should return None tuple
        email, name, account_id = extract_developer_from_jira_json("not a valid json")

        assert email is None
        assert name is None
        assert account_id is None

        # Unclosed braces
        email, name, account_id = extract_developer_from_jira_json(
            "{'emailAddress': 'test@example.com'"
        )

        assert email is None
        assert name is None
        assert account_id is None

    def test_double_quotes_json(self):
        """Test extraction with double-quoted JSON (valid Python dict string)."""
        # ast.literal_eval should handle both single and double quotes
        jira_json = '{"emailAddress": "test@example.com", "displayName": "Test User", "accountId": "acc-789"}'
        email, name, account_id = extract_developer_from_jira_json(jira_json)

        assert email == "test@example.com"
        assert name == "Test User"
        assert account_id == "acc-789"
