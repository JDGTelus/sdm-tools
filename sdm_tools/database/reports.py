"""Query-based report generation from normalized database."""

import os
import json
import sqlite3
from datetime import datetime, date
from rich.console import Console
from rich.table import Table
from ..config import DB_NAME
from ..utils import get_local_timezone, get_all_time_buckets

console = Console()


def query_daily_activity(target_date):
    """Query pre-aggregated daily activity for a specific date.
    
    Args:
        target_date: date object or string (YYYY-MM-DD)
    
    Returns:
        Dict with developers list and summary, or None if no data
    """
    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database not found. Please run refresh first.[/bold red]")
        return None
    
    # Convert to string if date object
    if isinstance(target_date, date):
        target_date = target_date.isoformat()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Get all activity for the date
        cursor.execute("""
            SELECT 
                d.id, d.name, d.email,
                das.time_bucket,
                das.jira_count, das.git_count, das.total_count,
                s.id as sprint_id, s.name as sprint_name, s.state as sprint_state
            FROM daily_activity_summary das
            JOIN developers d ON das.developer_id = d.id
            LEFT JOIN sprints s ON das.sprint_id = s.id
            WHERE das.activity_date = ?
              AND d.active = 1
            ORDER BY d.name, das.time_bucket
        """, (target_date,))
        
        rows = cursor.fetchall()
        
        if not rows:
            console.print(f"[yellow]No activity found for {target_date}[/yellow]")
            return None
        
        # Build developer activity structure
        developers_dict = {}
        sprint_context = None
        
        for row in rows:
            dev_id, name, email, time_bucket, jira, git, total, sprint_id, sprint_name, sprint_state = row
            
            # Capture sprint context (same for all rows on a given date)
            if sprint_id and not sprint_context:
                sprint_context = {
                    "id": sprint_id,
                    "name": sprint_name,
                    "state": sprint_state
                }
            
            # Initialize developer entry if needed
            if dev_id not in developers_dict:
                developers_dict[dev_id] = {
                    "name": name,
                    "email": email,
                    "buckets": {bucket: {"jira": 0, "git": 0, "total": 0} for bucket in ["8am-10am", "10am-12pm", "12pm-2pm", "2pm-4pm", "4pm-6pm"]},
                    "off_hours": {"jira": 0, "git": 0, "total": 0},
                    "daily_total": {"jira": 0, "git": 0, "total": 0}
                }
            
            # Add activity to appropriate bucket
            if time_bucket == "off_hours":
                developers_dict[dev_id]["off_hours"]["jira"] += jira
                developers_dict[dev_id]["off_hours"]["git"] += git
                developers_dict[dev_id]["off_hours"]["total"] += total
            else:
                developers_dict[dev_id]["buckets"][time_bucket]["jira"] += jira
                developers_dict[dev_id]["buckets"][time_bucket]["git"] += git
                developers_dict[dev_id]["buckets"][time_bucket]["total"] += total
            
            # Add to daily total
            developers_dict[dev_id]["daily_total"]["jira"] += jira
            developers_dict[dev_id]["daily_total"]["git"] += git
            developers_dict[dev_id]["daily_total"]["total"] += total
        
        # Convert to list and sort by total activity
        developers_list = list(developers_dict.values())
        developers_list.sort(key=lambda d: d['daily_total']['total'], reverse=True)
        
        # Calculate summary
        total_jira = sum(d['daily_total']['jira'] for d in developers_list)
        total_git = sum(d['daily_total']['git'] for d in developers_list)
        total_activity = sum(d['daily_total']['total'] for d in developers_list)
        
        # Find most active bucket
        bucket_totals = {}
        for bucket in get_all_time_buckets():
            if bucket == "off_hours":
                bucket_totals[bucket] = sum(d['off_hours']['total'] for d in developers_list)
            else:
                bucket_totals[bucket] = sum(d['buckets'][bucket]['total'] for d in developers_list)
        
        most_active_bucket = max(bucket_totals.items(), key=lambda x: x[1])[0] if bucket_totals else "N/A"
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
            "sprint_context": sprint_context
        }
        
        return result
        
    finally:
        conn.close()


def query_sprint_activity(sprint_id):
    """Query all activity for an entire sprint.
    
    Args:
        sprint_id: Sprint ID
    
    Returns:
        Dict with daily breakdown, developer summary, and metadata
    """
    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database not found. Please run refresh first.[/bold red]")
        return None
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Get sprint metadata
        cursor.execute("""
            SELECT id, name, state, start_date_local, end_date_local
            FROM sprints
            WHERE id = ?
        """, (sprint_id,))
        
        sprint_row = cursor.fetchone()
        if not sprint_row:
            console.print(f"[yellow]Sprint {sprint_id} not found[/yellow]")
            return None
        
        sprint_id, sprint_name, state, start_date, end_date = sprint_row
        
        # Get all activity for the sprint
        cursor.execute("""
            SELECT 
                das.activity_date,
                d.id, d.name, d.email,
                SUM(das.jira_count) as jira_count,
                SUM(das.git_count) as git_count,
                SUM(das.total_count) as total_count
            FROM daily_activity_summary das
            JOIN developers d ON das.developer_id = d.id
            WHERE das.sprint_id = ?
              AND d.active = 1
            GROUP BY das.activity_date, d.id
            ORDER BY das.activity_date, total_count DESC
        """, (sprint_id,))
        
        rows = cursor.fetchall()
        
        if not rows:
            console.print(f"[yellow]No activity found for sprint {sprint_name}[/yellow]")
            return None
        
        # Build daily breakdown
        daily_breakdown = {}
        developer_totals = {}
        
        for row in rows:
            activity_date, dev_id, name, email, jira, git, total = row
            
            # Daily breakdown
            if activity_date not in daily_breakdown:
                daily_breakdown[activity_date] = {
                    "date": activity_date,
                    "total_activity": 0,
                    "jira_actions": 0,
                    "git_actions": 0,
                    "active_developers": set()
                }
            
            daily_breakdown[activity_date]["total_activity"] += total
            daily_breakdown[activity_date]["jira_actions"] += jira
            daily_breakdown[activity_date]["git_actions"] += git
            daily_breakdown[activity_date]["active_developers"].add(dev_id)
            
            # Developer totals
            if dev_id not in developer_totals:
                developer_totals[dev_id] = {
                    "name": name,
                    "email": email,
                    "sprint_total": 0,
                    "sprint_jira": 0,
                    "sprint_git": 0,
                    "days_active": 0
                }
            
            developer_totals[dev_id]["sprint_total"] += total
            developer_totals[dev_id]["sprint_jira"] += jira
            developer_totals[dev_id]["sprint_git"] += git
            developer_totals[dev_id]["days_active"] += 1
        
        # Convert daily breakdown to list
        daily_list = []
        for date_key in sorted(daily_breakdown.keys()):
            day = daily_breakdown[date_key]
            day["active_developers"] = len(day["active_developers"])  # Convert set to count
            daily_list.append(day)
        
        # Convert developer totals to list and add avg_per_day
        developer_list = []
        for dev_data in developer_totals.values():
            dev_data["avg_per_day"] = round(dev_data["sprint_total"] / dev_data["days_active"], 1) if dev_data["days_active"] > 0 else 0
            developer_list.append(dev_data)
        
        developer_list.sort(key=lambda d: d["sprint_total"], reverse=True)
        
        # Calculate sprint summary
        sprint_total = sum(d["sprint_total"] for d in developer_list)
        avg_daily = round(sprint_total / len(daily_list), 1) if daily_list else 0
        most_active_day = max(daily_list, key=lambda d: d["total_activity"])["date"] if daily_list else None
        most_active_dev = developer_list[0]["name"] if developer_list else None
        
        # Calculate days count
        if start_date and end_date:
            from datetime import datetime
            start = datetime.fromisoformat(start_date).date()
            end = datetime.fromisoformat(end_date).date()
            days_total = (end - start).days + 1
            days_elapsed = len(daily_list)
        else:
            days_total = len(daily_list)
            days_elapsed = len(daily_list)
        
        result = {
            "sprint": {
                "id": sprint_id,
                "name": sprint_name,
                "state": state,
                "start_date": start_date,
                "end_date": end_date,
                "days_count": days_total,
                "days_elapsed": days_elapsed
            },
            "daily_breakdown": daily_list,
            "developer_summary": developer_list,
            "summary": {
                "sprint_total_activity": sprint_total,
                "avg_daily_activity": avg_daily,
                "most_active_day": most_active_day,
                "most_active_developer": most_active_dev
            }
        }
        
        return result
        
    finally:
        conn.close()


def query_date_range_activity(start_date, end_date):
    """Query activity for a date range.
    
    Args:
        start_date: Start date (date object or YYYY-MM-DD string)
        end_date: End date (date object or YYYY-MM-DD string)
    
    Returns:
        Dict with daily breakdown and summary
    """
    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database not found. Please run refresh first.[/bold red]")
        return None
    
    # Convert to strings if date objects
    if isinstance(start_date, date):
        start_date = start_date.isoformat()
    if isinstance(end_date, date):
        end_date = end_date.isoformat()
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Get sprints that overlap with the date range
        cursor.execute("""
            SELECT DISTINCT id, name
            FROM sprints
            WHERE (start_date_local <= ? AND end_date_local >= ?)
               OR (start_date_local >= ? AND start_date_local <= ?)
            ORDER BY start_date_local
        """, (end_date, start_date, start_date, end_date))
        
        sprints_included = [{"id": row[0], "name": row[1]} for row in cursor.fetchall()]
        
        # Get all activity for the date range
        cursor.execute("""
            SELECT 
                das.activity_date,
                d.id, d.name,
                SUM(das.jira_count) as jira_count,
                SUM(das.git_count) as git_count,
                SUM(das.total_count) as total_count
            FROM daily_activity_summary das
            JOIN developers d ON das.developer_id = d.id
            WHERE das.activity_date BETWEEN ? AND ?
              AND d.active = 1
            GROUP BY das.activity_date, d.id
            ORDER BY das.activity_date, total_count DESC
        """, (start_date, end_date))
        
        rows = cursor.fetchall()
        
        if not rows:
            console.print(f"[yellow]No activity found between {start_date} and {end_date}[/yellow]")
            return None
        
        # Build daily breakdown
        daily_breakdown = {}
        
        for row in rows:
            activity_date, dev_id, name, jira, git, total = row
            
            if activity_date not in daily_breakdown:
                daily_breakdown[activity_date] = {
                    "date": activity_date,
                    "total_activity": 0,
                    "jira_actions": 0,
                    "git_actions": 0,
                    "active_developers": set()
                }
            
            daily_breakdown[activity_date]["total_activity"] += total
            daily_breakdown[activity_date]["jira_actions"] += jira
            daily_breakdown[activity_date]["git_actions"] += git
            daily_breakdown[activity_date]["active_developers"].add(dev_id)
        
        # Convert to list
        daily_list = []
        for date_key in sorted(daily_breakdown.keys()):
            day = daily_breakdown[date_key]
            day["active_developers"] = len(day["active_developers"])
            daily_list.append(day)
        
        # Calculate summary
        total_activity = sum(d["total_activity"] for d in daily_list)
        avg_daily = round(total_activity / len(daily_list), 1) if daily_list else 0
        
        result = {
            "date_range": {
                "start_date": start_date,
                "end_date": end_date,
                "days_count": len(daily_list)
            },
            "sprints_included": sprints_included,
            "daily_breakdown": daily_list,
            "summary": {
                "total_activity": total_activity,
                "avg_daily_activity": avg_daily
            }
        }
        
        return result
        
    finally:
        conn.close()


def generate_daily_report_json(target_date=None, output_file=None):
    """Generate JSON report for a single day.
    
    Args:
        target_date: Date object or YYYY-MM-DD string (default: today)
        output_file: Output file path (default: ux/web/data/daily_activity_report.json)
    
    Returns:
        Path to generated file or None
    """
    # Default to today
    if target_date is None:
        tz = get_local_timezone()
        target_date = datetime.now(tz).date()
    elif isinstance(target_date, str):
        target_date = datetime.fromisoformat(target_date).date()
    
    # Default output file
    if output_file is None:
        output_file = "ux/web/data/daily_activity_report.json"
    
    console.print(f"\n[bold cyan]Generating Daily Activity Report for {target_date.isoformat()}...[/bold cyan]")
    
    # Query data
    data = query_daily_activity(target_date)
    
    if not data:
        return None
    
    # Build JSON structure
    tz = get_local_timezone()
    report = {
        "generated_at": datetime.now(tz).isoformat(),
        "report_type": "daily",
        "metadata": {
            "report_date": target_date.isoformat(),
            "timezone": str(tz),
            "time_buckets": ["8am-10am", "10am-12pm", "12pm-2pm", "2pm-4pm", "4pm-6pm"],
            "sprint": data.get("sprint_context")
        },
        "developers": data["developers"],
        "summary": data["summary"]
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write JSON
    try:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        console.print(f"[bold green]✓ Report generated: {output_file}[/bold green]")
        console.print(f"[dim]  Total activity: {data['summary']['total_activity']} ({data['summary']['total_developers']} developers)[/dim]")
        
        return output_file
    except Exception as e:
        console.print(f"[bold red]Error writing JSON: {e}[/bold red]")
        return None


def generate_sprint_report_json(sprint_id=None, output_file=None, limit=10):
    """Generate JSON report for sprints.
    
    By default, generates a multi-sprint report with the last 10 sprints (or fewer if less available).
    If sprint_id is provided, generates a single-sprint report for backward compatibility.
    
    Args:
        sprint_id: Optional specific Sprint ID (if None, generates multi-sprint report)
        output_file: Output file path (default: ux/web/data/sprint_activity_report.json)
        limit: Maximum number of sprints for multi-sprint report (default: 10)
    
    Returns:
        Path to generated file or None
    """
    if output_file is None:
        output_file = "ux/web/data/sprint_activity_report.json"
    
    # If sprint_id is provided, generate single sprint report (backward compatibility)
    if sprint_id is not None:
        console.print(f"\n[bold cyan]Generating Sprint Activity Report for Sprint {sprint_id}...[/bold cyan]")
        
        # Query data
        data = query_sprint_activity(sprint_id)
        
        if not data:
            return None
        
        # Build JSON structure
        tz = get_local_timezone()
        report = {
            "generated_at": datetime.now(tz).isoformat(),
            "report_type": "sprint",
            "metadata": data["sprint"],
            "daily_breakdown": data["daily_breakdown"],
            "developer_summary": data["developer_summary"],
            "summary": data["summary"]
        }
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Write JSON
        try:
            with open(output_file, 'w') as f:
                json.dump(report, f, indent=2)
            
            console.print(f"[bold green]✓ Report generated: {output_file}[/bold green]")
            console.print(f"[dim]  Sprint: {data['sprint']['name']}[/dim]")
            console.print(f"[dim]  Total activity: {data['summary']['sprint_total_activity']} ({len(data['developer_summary'])} developers)[/dim]")
            
            return output_file
        except Exception as e:
            console.print(f"[bold red]Error writing JSON: {e}[/bold red]")
            return None
    else:
        # Default to multi-sprint report
        return generate_multi_sprint_report_json(limit=limit, output_file=output_file)


def query_multi_sprint_activity(limit=10):
    """Query activity for multiple sprints (last N sprints).
    
    Args:
        limit: Maximum number of sprints to include (default: 10)
    
    Returns:
        Dict with sprints list and overall summary, or None if no data
    """
    if not os.path.exists(DB_NAME):
        console.print("[bold red]Database not found. Please run refresh first.[/bold red]")
        return None
    
    from .refresh import get_available_sprints
    
    # Get available sprints (already sorted by start_date DESC)
    available_sprints = get_available_sprints()
    
    if not available_sprints:
        console.print("[yellow]No sprints found in database[/yellow]")
        return None
    
    # Limit to requested number or available sprints, whichever is less
    sprints_to_query = available_sprints[:min(limit, len(available_sprints))]
    actual_count = len(sprints_to_query)
    
    console.print(f"[dim]Querying activity for {actual_count} sprint(s)...[/dim]")
    
    # Query each sprint
    sprints_data = []
    total_activity_across_sprints = 0
    all_developers = {}
    
    for sprint_id, name, state, start_date, end_date in sprints_to_query:
        sprint_activity = query_sprint_activity(sprint_id)
        
        if sprint_activity:
            sprints_data.append(sprint_activity)
            total_activity_across_sprints += sprint_activity['summary']['sprint_total_activity']
            
            # Aggregate developer participation
            for dev in sprint_activity['developer_summary']:
                dev_email = dev['email']
                if dev_email not in all_developers:
                    all_developers[dev_email] = {
                        'name': dev['name'],
                        'email': dev_email,
                        'total_activity': 0,
                        'sprints_participated': 0
                    }
                all_developers[dev_email]['total_activity'] += dev['sprint_total']
                all_developers[dev_email]['sprints_participated'] += 1
    
    if not sprints_data:
        console.print("[yellow]No activity data found for any sprint[/yellow]")
        return None
    
    # Find most active sprint
    most_active_sprint = max(sprints_data, key=lambda s: s['summary']['sprint_total_activity'])
    
    # Convert developer dict to sorted list
    developer_participation = sorted(
        all_developers.values(),
        key=lambda d: d['total_activity'],
        reverse=True
    )
    
    # Calculate overall summary
    avg_per_sprint = round(total_activity_across_sprints / len(sprints_data), 1) if sprints_data else 0
    
    result = {
        'sprints': sprints_data,
        'metadata': {
            'sprint_count': len(sprints_data),
            'requested_limit': limit,
            'earliest_sprint': {
                'id': sprints_data[-1]['sprint']['id'],
                'name': sprints_data[-1]['sprint']['name'],
                'start_date': sprints_data[-1]['sprint']['start_date']
            } if sprints_data else None,
            'latest_sprint': {
                'id': sprints_data[0]['sprint']['id'],
                'name': sprints_data[0]['sprint']['name'],
                'start_date': sprints_data[0]['sprint']['start_date']
            } if sprints_data else None
        },
        'overall_summary': {
            'total_sprints': len(sprints_data),
            'total_activity': total_activity_across_sprints,
            'avg_per_sprint': avg_per_sprint,
            'most_active_sprint': {
                'id': most_active_sprint['sprint']['id'],
                'name': most_active_sprint['sprint']['name'],
                'activity': most_active_sprint['summary']['sprint_total_activity']
            },
            'unique_developers': len(developer_participation),
            'developer_participation': developer_participation
        }
    }
    
    return result


def generate_multi_sprint_report_json(limit=10, output_file=None):
    """Generate JSON report for multiple sprints (last N sprints).
    
    Args:
        limit: Maximum number of sprints to include (default: 10)
        output_file: Output file path (default: ux/web/data/sprint_activity_report.json)
    
    Returns:
        Path to generated file or None
    """
    if output_file is None:
        output_file = "ux/web/data/sprint_activity_report.json"
    
    console.print(f"\n[bold cyan]Generating Multi-Sprint Activity Report (last {limit} sprints)...[/bold cyan]")
    
    # Query data
    data = query_multi_sprint_activity(limit)
    
    if not data:
        return None
    
    # Build JSON structure
    tz = get_local_timezone()
    report = {
        "generated_at": datetime.now(tz).isoformat(),
        "report_type": "multi_sprint",
        "metadata": data["metadata"],
        "sprints": data["sprints"],
        "overall_summary": data["overall_summary"]
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write JSON
    try:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        console.print(f"[bold green]✓ Multi-Sprint Report generated: {output_file}[/bold green]")
        console.print(f"[dim]  Sprints included: {data['metadata']['sprint_count']}[/dim]")
        console.print(f"[dim]  Total activity: {data['overall_summary']['total_activity']} ({data['overall_summary']['unique_developers']} developers)[/dim]")
        console.print(f"[dim]  Date range: {data['metadata']['earliest_sprint']['start_date']} to {data['metadata']['latest_sprint']['start_date']}[/dim]")
        
        return output_file
    except Exception as e:
        console.print(f"[bold red]Error writing JSON: {e}[/bold red]")
        return None


def generate_sprint_velocity_report(limit=10, output_file=None):
    """Generate sprint velocity report JSON file (Planned vs Delivered points).
    
    Args:
        limit: Number of recent sprints to include (default: 10)
        output_file: Output file path (default: ux/web/data/sprint_velocity_report.json)
    
    Returns:
        Path to generated file or None
    """
    from .sprint_metrics import calculate_sprint_velocity, get_sprint_velocity_summary
    
    # Default output file
    if output_file is None:
        output_file = 'ux/web/data/sprint_velocity_report.json'
    
    console.print(f'\n[bold cyan]Generating Sprint Velocity Report...[/bold cyan]')
    
    # Get sprint velocity data
    sprints_data = calculate_sprint_velocity(limit=limit)
    
    if not sprints_data:
        console.print('[bold red]No sprint data available[/bold red]')
        return None
    
    # Reverse to show oldest to newest (for chart progression left to right)
    sprints_data.reverse()
    
    # Get summary statistics
    summary = get_sprint_velocity_summary(limit=limit)
    
    # Build JSON structure
    tz = get_local_timezone()
    report = {
        'generated_at': datetime.now(tz).isoformat(),
        'report_type': 'sprint_velocity',
        'metadata': {
            'sprint_count': summary['sprint_count'],
            'earliest_sprint': {
                'id': sprints_data[0]['id'],
                'name': sprints_data[0]['name'],
                'start_date': sprints_data[0]['start_date']
            } if sprints_data else None,
            'latest_sprint': {
                'id': sprints_data[-1]['id'],
                'name': sprints_data[-1]['name'],
                'start_date': sprints_data[-1]['start_date']
            } if sprints_data else None,
            'total_planned_points': summary['total_planned_points'],
            'total_delivered_points': summary['total_delivered_points'],
            'avg_planned_per_sprint': summary['avg_planned_per_sprint'],
            'avg_delivered_per_sprint': summary['avg_delivered_per_sprint'],
            'overall_completion_rate': summary['overall_completion_rate']
        },
        'sprints': sprints_data
    }
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Write JSON
    try:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        console.print(f'[bold green]✓ Sprint Velocity Report generated: {output_file}[/bold green]')
        console.print(f'[dim]  Sprints analyzed: {summary["sprint_count"]}[/dim]')
        console.print(f'[dim]  Total Planned: {summary["total_planned_points"]} points[/dim]')
        console.print(f'[dim]  Total Delivered: {summary["total_delivered_points"]} points[/dim]')
        console.print(f'[dim]  Avg Completion Rate: {summary["overall_completion_rate"]}%[/dim]')
        
        return output_file
    except Exception as e:
        console.print(f'[bold red]Error writing JSON: {e}[/bold red]')
        return None
