"""UI and Timezone Utils"""

import re
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pyfiglet import Figlet
from rich.console import Console

console = Console()


def print_banner():
    """Prints the ASCII art banner."""
    f = Figlet(font="slant")
    ascii_art = f.renderText("SDM-Tools")
    console.print(f"[bold green]{ascii_art}[/bold green]")
    console.print("[bold blue]Customized insights and actions for SDMs.[/bold blue]")


def clear_screen():
    """Clears the terminal screen."""
    subprocess.run("clear", shell=True)


# ============================================================================
# Timezone and Date Utility Functions
# ============================================================================

def get_local_timezone(tz_string=None):
    """Returns ZoneInfo object for configured timezone.
    
    Args:
        tz_string: Timezone string (e.g., 'America/Mexico_City'). 
                   If None, uses TIMEZONE from config.
    
    Returns:
        ZoneInfo object
    """
    if tz_string is None:
        from .config import TIMEZONE
        tz_string = TIMEZONE
    
    try:
        return ZoneInfo(tz_string)
    except Exception as e:
        console.print(f"[bold yellow]Warning: Invalid timezone '{tz_string}', using UTC: {e}[/bold yellow]")
        return ZoneInfo('UTC')


def parse_git_date_to_local(date_str, target_tz=None):
    """Parse git date format and convert to local timezone.
    
    Git date format: "Wed Sep 17 23:37:12 2025 +0000"
    
    Args:
        date_str: Git date string with timezone offset
        target_tz: Target timezone string or ZoneInfo. If None, uses config TIMEZONE.
    
    Returns:
        datetime object in target timezone, or None if parsing fails
    """
    if not date_str:
        return None
    
    # Get target timezone
    if target_tz is None:
        target_tz = get_local_timezone()
    elif isinstance(target_tz, str):
        target_tz = get_local_timezone(target_tz)
    
    try:
        # Git format includes timezone: "Wed Sep 17 23:37:12 2025 +0000"
        # Parse with %z for timezone
        dt = datetime.strptime(date_str.strip(), "%a %b %d %H:%M:%S %Y %z")
        
        # Convert to target timezone
        local_dt = dt.astimezone(target_tz)
        return local_dt
        
    except ValueError as e:
        # Fallback: try parsing without timezone and assume UTC
        console.print(f"[bold yellow]Warning: Could not parse git date '{date_str}' with timezone, assuming UTC: {e}[/bold yellow]")
        try:
            # Remove timezone offset if present
            date_clean = re.sub(r'\s+[+-]\d{4}$', '', date_str.strip())
            dt = datetime.strptime(date_clean, "%a %b %d %H:%M:%S %Y")
            # Assume UTC and convert
            dt_utc = dt.replace(tzinfo=ZoneInfo('UTC'))
            return dt_utc.astimezone(target_tz)
        except Exception as fallback_e:
            console.print(f"[bold red]Error: Failed to parse git date '{date_str}': {fallback_e}[/bold red]")
            return None


def parse_jira_date_to_local(date_str, target_tz=None):
    """Parse Jira ISO date format and convert to local timezone.
    
    Jira date formats:
        - "2025-09-17T15:06:43.000+0000"
        - "2025-09-17T15:06:43.000Z"
        - "2025-09-17T15:06:43Z"
    
    Args:
        date_str: Jira ISO date string
        target_tz: Target timezone string or ZoneInfo. If None, uses config TIMEZONE.
    
    Returns:
        datetime object in target timezone, or None if parsing fails
    """
    if not date_str:
        return None
    
    # Get target timezone
    if target_tz is None:
        target_tz = get_local_timezone()
    elif isinstance(target_tz, str):
        target_tz = get_local_timezone(target_tz)
    
    try:
        # Replace 'Z' with '+00:00' for consistent parsing
        date_normalized = date_str.strip().replace('Z', '+00:00')
        
        # Try with milliseconds first: "2025-09-17T15:06:43.000+00:00"
        try:
            dt = datetime.strptime(date_normalized, "%Y-%m-%dT%H:%M:%S.%f%z")
        except ValueError:
            # Try without milliseconds: "2025-09-17T15:06:43+00:00"
            dt = datetime.strptime(date_normalized, "%Y-%m-%dT%H:%M:%S%z")
        
        # Convert to target timezone
        local_dt = dt.astimezone(target_tz)
        return local_dt
        
    except Exception as e:
        console.print(f"[bold red]Error: Failed to parse Jira date '{date_str}': {e}[/bold red]")
        return None


def get_time_bucket(dt):
    """Returns the time bucket name for a given datetime.
    
    Buckets:
        - "10am-12pm": 10:00-11:59
        - "12pm-2pm": 12:00-13:59
        - "2pm-4pm": 14:00-15:59
        - "4pm-6pm": 16:00-17:59
        - "off_hours": 18:00-07:59 (6pm to 8am)
        - None: 8:00-09:59 (not tracked)
    
    Args:
        dt: datetime object (should be timezone-aware)
    
    Returns:
        String bucket name or None if not in a tracked bucket
    """
    if not dt:
        return None
    
    hour = dt.hour
    
    if 10 <= hour < 12:
        return "10am-12pm"
    elif 12 <= hour < 14:
        return "12pm-2pm"
    elif 14 <= hour < 16:
        return "2pm-4pm"
    elif 16 <= hour < 18:
        return "4pm-6pm"
    elif hour >= 18 or hour < 8:
        return "off_hours"
    else:
        # 8am-10am not tracked
        return None


def is_within_time_bucket(dt, start_hour, end_hour):
    """Check if datetime falls within a time bucket.
    
    Args:
        dt: datetime object
        start_hour: Start hour (0-23)
        end_hour: End hour (0-23)
    
    Returns:
        Boolean
    """
    if not dt:
        return False
    
    hour = dt.hour
    
    # Handle overnight buckets (e.g., 18:00 to 08:00)
    if start_hour > end_hour:
        return hour >= start_hour or hour < end_hour
    else:
        return start_hour <= hour < end_hour


def is_off_hours(dt):
    """Check if datetime is in off-hours (6pm to 8am).
    
    Args:
        dt: datetime object
    
    Returns:
        Boolean
    """
    return is_within_time_bucket(dt, 18, 8)


def get_today_start_end(tz=None):
    """Get start and end datetime for today in the specified timezone.
    
    Args:
        tz: Timezone string or ZoneInfo. If None, uses config TIMEZONE.
    
    Returns:
        Tuple of (start_datetime, end_datetime) for today
        - start: Today at 00:00:00
        - end: Today at 23:59:59
    """
    if tz is None:
        tz = get_local_timezone()
    elif isinstance(tz, str):
        tz = get_local_timezone(tz)
    
    # Get current time in target timezone
    now = datetime.now(tz)
    
    # Start of day: 00:00:00
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # End of day: 23:59:59
    end = now.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    return start, end


def get_date_start_end(date_obj, tz=None):
    """Get start and end datetime for a specific date in the specified timezone.
    
    Args:
        date_obj: datetime.date or datetime object
        tz: Timezone string or ZoneInfo. If None, uses config TIMEZONE.
    
    Returns:
        Tuple of (start_datetime, end_datetime) for the date
        - start: Date at 00:00:00
        - end: Date at 23:59:59
    """
    if tz is None:
        tz = get_local_timezone()
    elif isinstance(tz, str):
        tz = get_local_timezone(tz)
    
    # If date_obj is a datetime, extract date
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    # Create datetime at start of day
    start = datetime.combine(date_obj, datetime.min.time()).replace(tzinfo=tz)
    
    # Create datetime at end of day
    end = datetime.combine(date_obj, datetime.max.time()).replace(tzinfo=tz)
    
    return start, end


def get_off_hours_window(date_obj, tz=None):
    """Get the off-hours window for a given date.
    
    Off-hours: 6pm previous day to 8am current day
    
    Args:
        date_obj: datetime.date or datetime object for the target day
        tz: Timezone string or ZoneInfo. If None, uses config TIMEZONE.
    
    Returns:
        Tuple of (start_datetime, end_datetime) for off-hours window
        - start: Previous day at 18:00:00 (6pm)
        - end: Current day at 07:59:59 (just before 8am)
    """
    if tz is None:
        tz = get_local_timezone()
    elif isinstance(tz, str):
        tz = get_local_timezone(tz)
    
    # If date_obj is a datetime, extract date
    if isinstance(date_obj, datetime):
        date_obj = date_obj.date()
    
    # Start: Previous day at 6pm
    prev_day = date_obj - timedelta(days=1)
    start = datetime.combine(prev_day, datetime.min.time()).replace(hour=18, minute=0, second=0, microsecond=0, tzinfo=tz)
    
    # End: Current day at 7:59:59 (just before 8am)
    end = datetime.combine(date_obj, datetime.min.time()).replace(hour=7, minute=59, second=59, microsecond=999999, tzinfo=tz)
    
    return start, end


def get_all_time_buckets():
    """Returns list of all time bucket names in order.
    
    Returns:
        List of bucket name strings
    """
    return ["10am-12pm", "12pm-2pm", "2pm-4pm", "4pm-6pm", "off_hours"]


def format_datetime_local(dt, fmt="%Y-%m-%d %H:%M:%S %Z"):
    """Format datetime with timezone information.
    
    Args:
        dt: datetime object (timezone-aware)
        fmt: strftime format string
    
    Returns:
        Formatted string
    """
    if not dt:
        return "N/A"
    
    return dt.strftime(fmt)
