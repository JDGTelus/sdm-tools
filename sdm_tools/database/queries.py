"""Query functions for simplified 3-table schema."""

import sqlite3
from datetime import datetime, date
from rich.console import Console
from ..config import DB_NAME, TIMEZONE

console = Console()


def hour_to_bucket(hour):
    """Convert hour (0-23) to time bucket name.
    
    Args:
        hour: Hour of day (0-23)
    
    Returns:
        Time bucket name
    """
    if 8 <= hour < 10:
        return '8am-10am'
    elif 10 <= hour < 12:
        return '10am-12pm'
    elif 12 <= hour < 14:
        return '12pm-2pm'
    elif 14 <= hour < 16:
        return '2pm-4pm'
    elif 16 <= hour < 18:
        return '4pm-6pm'
    else:
        return 'off_hours'


def query_daily_activity(target_date):
    """Query daily activity for a specific date from simplified schema.
    
    Args:
        target_date: date object or string (YYYY-MM-DD)
    
    Returns:
        Dict with developers list and summary, or None if no data
    """
    if isinstance(target_date, date):
        target_date = target_date.isoformat()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # First, get all active developers
        cursor.execute("""
            SELECT email, name
            FROM developers
            WHERE active = 1
            ORDER BY name
        """)
        
        all_active_devs = cursor.fetchall()
        
        if not all_active_devs:
            console.print("[yellow]No active developers configured[/yellow]")
            return None
        
        # Initialize structure for all active developers
        developers_dict = {}
        for email, name in all_active_devs:
            developers_dict[email] = {
                "name": name,
                "email": email,
                "buckets": {
                    "8am-10am": {"jira": 0, "git": 0, "total": 0},
                    "10am-12pm": {"jira": 0, "git": 0, "total": 0},
                    "12pm-2pm": {"jira": 0, "git": 0, "total": 0},
                    "2pm-4pm": {"jira": 0, "git": 0, "total": 0},
                    "4pm-6pm": {"jira": 0, "git": 0, "total": 0}
                },
                "off_hours": {"jira": 0, "git": 0, "total": 0},
                "daily_total": {"jira": 0, "git": 0, "total": 0}
            }
        
        # Now get activity for the date
        cursor.execute("""
            SELECT 
                developer_email,
                event_type,
                event_timestamp,
                sprint_name
            FROM activity_events
            WHERE event_date = ?
            ORDER BY developer_email, event_timestamp
        """, (target_date,))
        
        rows = cursor.fetchall()
        sprint_context = None
        
        # Process events and bucket them
        for developer_email, event_type, event_timestamp, sprint_name in rows:
            if developer_email not in developers_dict:
                continue  # Skip inactive developers
            
            # Capture sprint context (first non-null sprint name)
            if sprint_name and not sprint_context:
                sprint_context = {"name": sprint_name}
            
            # Determine source (jira or git)
            source = "jira" if event_type.startswith("jira") else "git"
            
            # Get time bucket from timestamp
            try:
                # Parse timestamp to get hour
                if 'T' in event_timestamp:
                    dt = datetime.fromisoformat(event_timestamp.replace('Z', '+00:00'))
                    from pytz import timezone as pytz_timezone
                    tz = pytz_timezone(TIMEZONE)
                    if dt.tzinfo:
                        dt = dt.astimezone(tz)
                    else:
                        dt = tz.localize(dt)
                    hour = dt.hour
                else:
                    hour = 0  # Default to off_hours if can't parse
                
                bucket = hour_to_bucket(hour)
            except:
                bucket = 'off_hours'
            
            # Increment counters
            if bucket == 'off_hours':
                developers_dict[developer_email]["off_hours"][source] += 1
                developers_dict[developer_email]["off_hours"]["total"] += 1
            else:
                developers_dict[developer_email]["buckets"][bucket][source] += 1
                developers_dict[developer_email]["buckets"][bucket]["total"] += 1
            
            developers_dict[developer_email]["daily_total"][source] += 1
            developers_dict[developer_email]["daily_total"]["total"] += 1
        
        # Convert to list and sort by total activity
        developers_list = list(developers_dict.values())
        developers_list.sort(key=lambda d: d['daily_total']['total'], reverse=True)
        
        # Calculate summary
        total_jira = sum(d['daily_total']['jira'] for d in developers_list)
        total_git = sum(d['daily_total']['git'] for d in developers_list)
        total_activity = sum(d['daily_total']['total'] for d in developers_list)
        
        # Find most active bucket
        bucket_totals = {}
        for bucket in ['8am-10am', '10am-12pm', '12pm-2pm', '2pm-4pm', '4pm-6pm', 'off_hours']:
            if bucket == 'off_hours':
                bucket_totals[bucket] = sum(d['off_hours']['total'] for d in developers_list)
            else:
                bucket_totals[bucket] = sum(d['buckets'][bucket]['total'] for d in developers_list)
        
        # Find most active bucket (excluding off_hours for this metric)
        work_hours_buckets = {k: v for k, v in bucket_totals.items() if k != 'off_hours'}
        if work_hours_buckets and any(count > 0 for count in work_hours_buckets.values()):
            most_active_bucket = max(work_hours_buckets.items(), key=lambda x: x[1])[0]
        else:
            most_active_bucket = "N/A"
        
        off_hours_total = bucket_totals.get('off_hours', 0)
        off_hours_pct = round((off_hours_total / total_activity * 100), 1) if total_activity > 0 else 0
        
        result = {
            "developers": developers_list,
            "summary": {
                "total_developers": len(developers_list),
                "total_activity": total_activity,
                "total_jira_actions": total_jira,
                "total_repo_actions": total_git,
                "most_active_bucket": most_active_bucket,
                "off_hours_activity": off_hours_total,
                "off_hours_percentage": off_hours_pct,
                "bucket_totals": bucket_totals
            },
            "metadata": {
                "report_date": target_date,
                "timezone": TIMEZONE,
                "time_buckets": ['8am-10am', '10am-12pm', '12pm-2pm', '2pm-4pm', '4pm-6pm'],
                "sprint": sprint_context
            }
        }
        
        return result
        
    except Exception as e:
        console.print(f"[bold red]Error querying daily activity: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        return None
    finally:
        conn.close()


def get_database_stats(conn=None):
    """Get statistics about the database.
    
    Args:
        conn: SQLite connection (optional, will create if not provided)
    
    Returns:
        Dict with table counts
    """
    close_conn = False
    if conn is None:
        conn = sqlite3.connect(DB_NAME)
        close_conn = True
    
    cursor = conn.cursor()
    stats = {}
    
    try:
        # Developers
        cursor.execute("SELECT COUNT(*) FROM developers WHERE active = 1")
        stats['active_developers'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM developers")
        stats['total_developers'] = cursor.fetchone()[0]
        
        # Sprints
        cursor.execute("SELECT COUNT(*) FROM sprints")
        stats['sprints'] = cursor.fetchone()[0]
        
        # Events by type
        cursor.execute("SELECT event_type, COUNT(*) FROM activity_events GROUP BY event_type")
        events_by_type = dict(cursor.fetchall())
        stats['events_by_type'] = events_by_type
        stats['total_events'] = sum(events_by_type.values())
        
        return stats
    finally:
        if close_conn:
            conn.close()
