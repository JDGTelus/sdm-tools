"""Sprint velocity and metrics reporting."""

import os
import sqlite3
from rich.console import Console
from ..config import DB_NAME

console = Console()


def calculate_sprint_velocity(sprint_id=None, limit=10):
    """Calculate planned vs delivered story points for sprints.
    
    Business Logic:
    - PLANNED: Sum of story points for issues assigned to sprint that were 
               created BEFORE the sprint start date
    - DELIVERED: Sum of story points for issues that were marked as 
                 Done/Closed BY the sprint end date
    
    Args:
        sprint_id: Specific sprint ID or None for recent sprints
        limit: Number of recent sprints to analyze (default: 10)
    
    Returns:
        List of dicts with sprint velocity data, ordered by start_date DESC
    """
    if not os.path.exists(DB_NAME):
        console.print('[bold red]Database not found. Please run refresh first.[/bold red]')
        return []
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        # Check if story_points column exists
        cursor.execute("PRAGMA table_info(issues)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'story_points' not in columns:
            console.print('[bold red]Error: story_points column not found in issues table.[/bold red]')
            console.print('[yellow]The database schema needs to be updated.[/yellow]')
            console.print('[yellow]Please run a full data refresh to add the story_points column:[/yellow]')
            console.print('[cyan]  1. Go to main menu[/cyan]')
            console.print('[cyan]  2. Choose option 1: "Refresh All Data"[/cyan]')
            console.print('[cyan]  3. Confirm with "yes"[/cyan]')
            console.print('[dim]This will backup your current database and create a new schema with story points support.[/dim]')
            return []
        
        # Build query
        where_clause = f"WHERE s.id = {sprint_id}" if sprint_id else ""
        limit_clause = f"LIMIT {limit}" if not sprint_id else ""
        
        # Build WHERE clause with NULL date filter
        base_where = "WHERE s.start_date_local IS NOT NULL AND s.end_date_local IS NOT NULL"
        if sprint_id:
            full_where = f"{base_where} AND s.id = {sprint_id}"
        else:
            full_where = base_where
        
        query = f"""
        SELECT 
            s.id,
            s.name,
            s.start_date_local,
            s.end_date_local,
            s.state,
            
            -- PLANNED POINTS: Issues in sprint, created before sprint start
            COALESCE(SUM(
                CASE 
                    WHEN i.created_date_local < s.start_date_local 
                    THEN i.story_points 
                    ELSE 0 
                END
            ), 0) as planned_points,
            
            -- DELIVERED POINTS: Issues completed by sprint end
            COALESCE(SUM(
                CASE 
                    WHEN i.status_name IN ('Done', 'Closed') 
                    AND i.status_changed_date_local <= s.end_date_local
                    THEN i.story_points 
                    ELSE 0 
                END
            ), 0) as delivered_points,
            
            -- Issue counts for context
            COUNT(DISTINCT isp.issue_id) as total_issues,
            COUNT(DISTINCT CASE 
                WHEN i.status_name IN ('Done', 'Closed') 
                AND i.status_changed_date_local <= s.end_date_local
                THEN isp.issue_id 
            END) as completed_issues,
            
            -- Count issues created before sprint start (planned issues)
            COUNT(DISTINCT CASE 
                WHEN i.created_date_local < s.start_date_local
                THEN isp.issue_id 
            END) as planned_issues
            
        FROM sprints s
        LEFT JOIN issue_sprints isp ON s.id = isp.sprint_id
        LEFT JOIN issues i ON isp.issue_id = i.id
        {full_where}
        GROUP BY s.id, s.name, s.start_date_local, s.end_date_local, s.state
        ORDER BY s.start_date_local DESC
        {limit_clause}
        """
        
        cursor.execute(query)
        
        results = []
        for row in cursor.fetchall():
            sprint_data = {
                'id': row[0],
                'name': row[1],
                'start_date': row[2],
                'end_date': row[3],
                'state': row[4],
                'planned_points': round(row[5], 1) if row[5] else 0.0,
                'delivered_points': round(row[6], 1) if row[6] else 0.0,
                'completion_rate': round((row[6] / row[5] * 100), 1) if row[5] > 0 else 0.0,
                'total_issues': row[7],
                'completed_issues': row[8],
                'planned_issues': row[9]
            }
            results.append(sprint_data)
        
        return results
    
    except sqlite3.OperationalError as e:
        if 'no such column' in str(e).lower():
            console.print(f'[bold red]Database Error: {str(e)}[/bold red]')
            console.print('[yellow]The database schema is missing required columns.[/yellow]')
            console.print('[yellow]Please run a full data refresh:[/yellow]')
            console.print('[cyan]  1. Return to main menu[/cyan]')
            console.print('[cyan]  2. Choose option 1: "Refresh All Data (Jira + Git → Normalize)"[/cyan]')
            console.print('[cyan]  3. Confirm with "yes"[/cyan]')
            console.print('[dim]This will add the story_points column and populate it with data from Jira.[/dim]')
        else:
            console.print(f'[bold red]Database Error: {str(e)}[/bold red]')
        return []
        
    finally:
        conn.close()


def get_sprint_velocity_summary(limit=10):
    """Get summary statistics for sprint velocity across multiple sprints.
    
    Args:
        limit: Number of recent sprints to analyze
    
    Returns:
        Dict with overall statistics
    """
    sprints = calculate_sprint_velocity(limit=limit)
    
    if not sprints:
        return {
            'sprint_count': 0,
            'total_planned_points': 0.0,
            'total_delivered_points': 0.0,
            'avg_planned_per_sprint': 0.0,
            'avg_delivered_per_sprint': 0.0,
            'overall_completion_rate': 0.0
        }
    
    total_planned = sum(s['planned_points'] for s in sprints)
    total_delivered = sum(s['delivered_points'] for s in sprints)
    
    return {
        'sprint_count': len(sprints),
        'total_planned_points': round(total_planned, 1),
        'total_delivered_points': round(total_delivered, 1),
        'avg_planned_per_sprint': round(total_planned / len(sprints), 1),
        'avg_delivered_per_sprint': round(total_delivered / len(sprints), 1),
        'overall_completion_rate': round((total_delivered / total_planned * 100), 1) if total_planned > 0 else 0.0
    }


def display_sprint_velocity(limit=10):
    """Display sprint velocity data in a formatted table.
    
    Args:
        limit: Number of recent sprints to display
    """
    from rich.table import Table
    
    sprints = calculate_sprint_velocity(limit=limit)
    
    if not sprints:
        console.print('[bold yellow]No sprint velocity data available[/bold yellow]')
        return
    
    # Reverse to show oldest first
    sprints.reverse()
    
    table = Table(show_header=True, header_style='bold cyan')
    table.add_column('Sprint', style='cyan')
    table.add_column('Start Date', style='dim')
    table.add_column('End Date', style='dim')
    table.add_column('Planned', justify='right', style='yellow')
    table.add_column('Delivered', justify='right', style='green')
    table.add_column('Rate', justify='right', style='magenta')
    table.add_column('Issues', justify='right', style='blue')
    
    for sprint in sprints:
        name_short = sprint['name'].replace('DevicesTITAN_', '')
        completion_color = 'green' if sprint['completion_rate'] >= 80 else 'yellow' if sprint['completion_rate'] >= 60 else 'red'
        
        table.add_row(
            name_short,
            sprint['start_date'],
            sprint['end_date'],
            f"{sprint['planned_points']} pts",
            f"{sprint['delivered_points']} pts",
            f"[{completion_color}]{sprint['completion_rate']}%[/{completion_color}]",
            f"{sprint['completed_issues']}/{sprint['total_issues']}"
        )
    
    console.print(table)
    
    # Display summary
    summary = get_sprint_velocity_summary(limit=limit)
    console.print(f"\n[bold cyan]Summary Statistics:[/bold cyan]")
    console.print(f"  Total Planned: {summary['total_planned_points']} points")
    console.print(f"  Total Delivered: {summary['total_delivered_points']} points")
    console.print(f"  Avg Planned/Sprint: {summary['avg_planned_per_sprint']} points")
    console.print(f"  Avg Delivered/Sprint: {summary['avg_delivered_per_sprint']} points")
    console.print(f"  Overall Completion Rate: {summary['overall_completion_rate']}%")
