"""Email normalization utilities for developer matching."""

import re


def normalize_email(email):
    """Normalize email to canonical form with auto-mapping patterns.
    
    Handles:
        - AWS SSO prefixes: AWSReservedSSO_xxx/user@domain.com -> user@domain.com
        - Case sensitivity: User@Domain.com -> user@domain.com
        - Domain variations: @telusinternational.com -> @telus.com
        - Numeric suffixes: carlos.carias01@telus.com -> carlos.carias@telus.com
    
    Args:
        email: Raw email string
    
    Returns:
        Normalized email string or None
    """
    if not email or email == 'Unknown':
        return None
    
    # 1. Strip whitespace
    email = email.strip()
    
    # 2. Remove AWS SSO prefix
    # Pattern: "AWSReservedSSO_TELUS-IoT-Developer_xxx/user@domain.com"
    if '/' in email and email.startswith('AWSReservedSSO'):
        email = email.split('/')[-1]
    
    # 3. Lowercase
    email = email.lower()
    
    # 4. Domain normalization - map telusinternational.com to telus.com
    email = email.replace('@telusinternational.com', '@telus.com')
    
    # 5. Remove numeric suffixes before @ (e.g., carlos.carias01 -> carlos.carias)
    # Only remove trailing digits in the local part
    email = re.sub(r'(\d+)@', '@', email)
    
    return email


def extract_developer_from_jira_json(jira_json_str):
    """Extract developer info from Jira assignee/creator/reporter JSON string.
    
    Args:
        jira_json_str: JSON string like "{'emailAddress': '...', 'displayName': '...'}"
    
    Returns:
        Tuple of (normalized_email, display_name, account_id) or (None, None, None)
    """
    if not jira_json_str:
        return None, None, None
    
    try:
        import ast
        data = ast.literal_eval(jira_json_str)
        
        raw_email = data.get('emailAddress', '')
        email = normalize_email(raw_email)
        name = data.get('displayName', '')
        account_id = data.get('accountId', '')
        
        return email, name, account_id
    except Exception:
        # Silent failure - skip malformed JSON
        return None, None, None
