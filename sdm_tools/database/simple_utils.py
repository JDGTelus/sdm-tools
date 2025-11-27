"""Utility functions for simplified database operations."""

import json
import re
from datetime import datetime

import pytz

from ..config import INCLUDED_EMAILS, TIMEZONE


def normalize_email(email):
    """Normalize email address for consistent matching.

    Handles:
    - AWS SSO prefixes: AWSReservedSSO_*/user@domain.com -> user@domain.com
    - Domain variations: @telusinternational.com -> @telus.com
    - Numeric suffixes: user01@domain.com -> user@domain.com
    - Case normalization: all lowercase

    Args:
        email: Raw email address

    Returns:
        Normalized email address
    """
    if not email:
        return None

    email = email.lower().strip()

    # Remove AWS SSO prefix
    if "awsreservedsso" in email:
        parts = email.split("/")
        if len(parts) > 1:
            email = parts[-1]

    # Normalize domain
    email = email.replace("@telusinternational.com", "@telus.com")

    # Remove numeric suffixes before @
    email = re.sub(r"\d+@", "@", email)

    return email


def is_developer_active(email):
    """Check if developer email is in the active list.

    Args:
        email: Normalized email address

    Returns:
        Boolean indicating if developer is active
    """
    if not INCLUDED_EMAILS:
        return True  # If no filter specified, all are active

    normalized_email = normalize_email(email)
    normalized_included = [normalize_email(e) for e in INCLUDED_EMAILS]

    return normalized_email in normalized_included


def get_time_bucket(timestamp_str):
    """Convert ISO timestamp to time bucket.

    Time buckets:
    - 8am-10am: 08:00-09:59
    - 10am-12pm: 10:00-11:59
    - 12pm-2pm: 12:00-13:59
    - 2pm-4pm: 14:00-15:59
    - 4pm-6pm: 16:00-17:59
    - off_hours: All other times

    Args:
        timestamp_str: ISO 8601 timestamp string

    Returns:
        Time bucket name (e.g., '10am-12pm' or 'off_hours')
    """
    try:
        # Parse timestamp (handle both with and without timezone)
        if "T" in timestamp_str:
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(timestamp_str)
        else:
            dt = datetime.fromisoformat(timestamp_str)

        # Convert to local timezone
        tz = pytz.timezone(TIMEZONE)
        dt = tz.localize(dt) if dt.tzinfo is None else dt.astimezone(tz)

        hour = dt.hour

        # Determine bucket
        if 8 <= hour < 10:
            return "8am-10am"
        elif 10 <= hour < 12:
            return "10am-12pm"
        elif 12 <= hour < 14:
            return "12pm-2pm"
        elif 14 <= hour < 16:
            return "2pm-4pm"
        elif 16 <= hour < 18:
            return "4pm-6pm"
        else:
            return "off_hours"

    except Exception as e:
        print(f"Error parsing timestamp {timestamp_str}: {e}")
        return "off_hours"


def get_local_date(timestamp_str):
    """Extract local date from ISO timestamp.

    Args:
        timestamp_str: ISO 8601 timestamp string

    Returns:
        Date string in YYYY-MM-DD format
    """
    try:
        if "T" in timestamp_str:
            if timestamp_str.endswith("Z"):
                timestamp_str = timestamp_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(timestamp_str)
        else:
            dt = datetime.fromisoformat(timestamp_str)

        # Convert to local timezone
        tz = pytz.timezone(TIMEZONE)
        dt = tz.localize(dt) if dt.tzinfo is None else dt.astimezone(tz)

        return dt.date().isoformat()

    except Exception as e:
        print(f"Error parsing timestamp {timestamp_str}: {e}")
        return None


def find_sprint_for_date(date_str, sprints):
    """Find which sprint a date falls into.

    Args:
        date_str: Date in YYYY-MM-DD format
        sprints: List of sprint dicts with start_date and end_date

    Returns:
        Sprint name or None
    """
    if not date_str or not sprints:
        return None

    from datetime import date

    try:
        target_date = date.fromisoformat(date_str)
    except:
        return None

    for sprint in sprints:
        if not sprint.get("start_date") or not sprint.get("end_date"):
            continue

        try:
            start = date.fromisoformat(sprint["start_date"])
            end = date.fromisoformat(sprint["end_date"])

            if start <= target_date <= end:
                return sprint["name"]
        except:
            continue

    return None


def create_metadata_json(**kwargs):
    """Create JSON metadata blob from keyword arguments.

    Args:
        **kwargs: Any metadata fields

    Returns:
        JSON string
    """
    # Filter out None values
    metadata = {k: v for k, v in kwargs.items() if v is not None}
    return json.dumps(metadata) if metadata else None


def parse_metadata_json(json_str):
    """Parse JSON metadata blob.

    Args:
        json_str: JSON string

    Returns:
        Dict of metadata or empty dict
    """
    if not json_str:
        return {}

    try:
        return json.loads(json_str)
    except:
        return {}


def get_all_time_buckets():
    """Get list of all time buckets in order.

    Returns:
        List of bucket names
    """
    return ["8am-10am", "10am-12pm", "12pm-2pm", "2pm-4pm", "4pm-6pm", "off_hours"]
