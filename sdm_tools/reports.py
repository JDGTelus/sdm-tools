"""
SDM Tools - Advanced Reporting Module
Generates cross-referenced reports combining Jira, Git commits, pull requests, and merges
"""
import sqlite3
import json
import re
from datetime import datetime
from collections import defaultdict
from .utils import console
from .team_filter import TeamMemberExtractor, get_team_filter_conditions
from rich.table import Table
from rich.panel import Panel


class SDMReporter:
    def __init__(self, db_path="sdm_tools.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        
    def close(self):
        self.conn.close()
    
    def extract_email_from_assignee(self, assignee_json):
        """Extract email from Jira assignee JSON string"""
        try:
            if assignee_json:
                assignee_data = json.loads(assignee_json)
                return assignee_data.get('emailAddress', assignee_data.get('displayName', 'Unknown'))
        except (json.JSONDecodeError, TypeError):
            pass
        return 'Unknown'
    
    def extract_display_name_from_assignee(self, assignee_json):
        """Extract display name from Jira assignee JSON string"""
        try:
            if assignee_json:
                assignee_data = json.loads(assignee_json)
                return assignee_data.get('displayName', 'Unknown')
        except (json.JSONDecodeError, TypeError):
            pass
        return 'Unknown'
    
    def extract_status_name(self, status_json):
        """Extract status name from Jira status JSON string"""
        try:
            if status_json:
                status_data = json.loads(status_json)
                return status_data.get('name', 'Unknown')
        except (json.JSONDecodeError, TypeError):
            pass
        return 'Unknown'
    
    def create_developer_activity_view(self):
        """Create a database view for developer activity analysis (team-filtered)"""
        # First ensure team_members table exists
        extractor = TeamMemberExtractor(self.db_path)
        try:
            extractor.create_team_member_table()
        finally:
            extractor.close()
        
        view_sql = """
        CREATE VIEW IF NOT EXISTS team_developer_activity_summary AS
        SELECT 
            COALESCE(gc.author_email, pr.author, cm.author_email) as developer_email,
            COALESCE(gc.author_name, pr.author, cm.author_name) as developer_name,
            COUNT(DISTINCT gc.hash) as commit_count,
            COUNT(DISTINCT pr.id) as pull_request_count,
            COUNT(DISTINCT cm.hash) as merge_count,
            MIN(COALESCE(gc.date, pr.creation_date, cm.date)) as first_activity,
            MAX(COALESCE(gc.date, pr.last_activity_date, cm.date)) as last_activity
        FROM 
            (SELECT DISTINCT author_email, author_name, date, hash FROM git_commits 
             WHERE EXISTS (
                 SELECT 1 FROM team_members tm 
                 WHERE author_email = tm.email_address 
                    OR author_name = tm.display_name
             )) gc
        FULL OUTER JOIN 
            (SELECT DISTINCT author, creation_date, last_activity_date, id FROM codecommit_pull_requests
             WHERE EXISTS (
                 SELECT 1 FROM team_members tm 
                 WHERE author = tm.email_address 
                    OR author = tm.display_name
             )) pr 
            ON gc.author_email = pr.author OR gc.author_name = pr.author
        FULL OUTER JOIN 
            (SELECT DISTINCT author_email, author_name, date, hash FROM codecommit_merges
             WHERE EXISTS (
                 SELECT 1 FROM team_members tm 
                 WHERE author_email = tm.email_address 
                    OR author_name = tm.display_name
             )) cm 
            ON gc.author_email = cm.author_email OR pr.author = cm.author_email
        WHERE COALESCE(gc.author_email, pr.author, cm.author_email) IS NOT NULL
        GROUP BY 
            COALESCE(gc.author_email, pr.author, cm.author_email),
            COALESCE(gc.author_name, pr.author, cm.author_name)
        ORDER BY commit_count DESC, pull_request_count DESC, merge_count DESC;
        """
        
        self.conn.execute("DROP VIEW IF EXISTS team_developer_activity_summary")
        self.conn.execute(view_sql)
        self.conn.commit()
        console.print("[green]✓ Created team_developer_activity_summary view (team-filtered)[/green]")
    
    def create_jira_git_correlation_view(self):
        """Create a view correlating Jira tickets with Git activity"""
        view_sql = """
        CREATE VIEW IF NOT EXISTS jira_git_correlation AS
        SELECT 
            j.id as jira_id,
            j.summary,
            json_extract(j.assignee, '$.emailAddress') as assignee_email,
            json_extract(j.assignee, '$.displayName') as assignee_name,
            json_extract(j.status, '$.name') as status,
            j.created as jira_created,
            j.updated as jira_updated,
            COUNT(DISTINCT gc.hash) as related_commits,
            COUNT(DISTINCT pr.id) as related_pull_requests,
            COUNT(DISTINCT cm.hash) as related_merges,
            GROUP_CONCAT(DISTINCT gc.author_email) as commit_authors,
            MIN(gc.date) as first_commit_date,
            MAX(gc.date) as last_commit_date
        FROM iotmi_3p_issues j
        LEFT JOIN git_commits gc ON (
            gc.message LIKE '%' || j.id || '%' OR
            gc.author_email = json_extract(j.assignee, '$.emailAddress')
        )
        LEFT JOIN codecommit_pull_requests pr ON (
            pr.title LIKE '%' || j.id || '%' OR
            pr.author = json_extract(j.assignee, '$.emailAddress')
        )
        LEFT JOIN codecommit_merges cm ON (
            cm.message LIKE '%' || j.id || '%' OR
            cm.author_email = json_extract(j.assignee, '$.emailAddress')
        )
        GROUP BY j.id, j.summary, j.assignee, j.status, j.created, j.updated
        ORDER BY related_commits DESC, related_pull_requests DESC;
        """
        
        self.conn.execute("DROP VIEW IF EXISTS jira_git_correlation")
        self.conn.execute(view_sql)
        self.conn.commit()
        console.print("[green]✓ Created jira_git_correlation view[/green]")
    
    def get_developer_productivity_report(self):
        """Generate comprehensive developer productivity report (team-filtered)"""
        query = """
        SELECT 
            developer_email,
            developer_name,
            commit_count,
            pull_request_count,
            merge_count,
            first_activity,
            last_activity,
            CASE 
                WHEN commit_count > 50 THEN 'High'
                WHEN commit_count > 20 THEN 'Medium'
                ELSE 'Low'
            END as activity_level
        FROM team_developer_activity_summary
        WHERE developer_email IS NOT NULL AND developer_email != ''
        ORDER BY commit_count DESC, pull_request_count DESC;
        """
        
        cursor = self.conn.execute(query)
        results = cursor.fetchall()
        
        table = Table(title="Developer Productivity Report")
        table.add_column("Developer", style="cyan")
        table.add_column("Email", style="blue")
        table.add_column("Commits", justify="right", style="green")
        table.add_column("Pull Requests", justify="right", style="yellow")
        table.add_column("Merges", justify="right", style="magenta")
        table.add_column("Activity Level", style="bold")
        table.add_column("First Activity", style="dim")
        table.add_column("Last Activity", style="dim")
        
        for row in results:
            activity_color = {
                'High': 'green',
                'Medium': 'yellow', 
                'Low': 'red'
            }.get(row['activity_level'], 'white')
            
            table.add_row(
                row['developer_name'] or 'Unknown',
                row['developer_email'] or 'Unknown',
                str(row['commit_count']),
                str(row['pull_request_count']),
                str(row['merge_count']),
                f"[{activity_color}]{row['activity_level']}[/{activity_color}]",
                row['first_activity'][:10] if row['first_activity'] else 'N/A',
                row['last_activity'][:10] if row['last_activity'] else 'N/A'
            )
        
        return table
    
    def get_jira_completion_analysis(self):
        """Analyze Jira ticket completion patterns"""
        query = """
        SELECT 
            json_extract(assignee, '$.displayName') as assignee_name,
            json_extract(assignee, '$.emailAddress') as assignee_email,
            json_extract(status, '$.name') as status,
            COUNT(*) as ticket_count,
            AVG(julianday(updated) - julianday(created)) as avg_completion_days
        FROM iotmi_3p_issues
        WHERE assignee IS NOT NULL AND assignee != 'null' AND json_valid(assignee)
        GROUP BY assignee_email, status
        ORDER BY assignee_email, ticket_count DESC;
        """
        
        cursor = self.conn.execute(query)
        results = cursor.fetchall()
        
        table = Table(title="Jira Ticket Completion Analysis")
        table.add_column("Assignee", style="cyan")
        table.add_column("Email", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Ticket Count", justify="right", style="green")
        table.add_column("Avg Days", justify="right", style="magenta")
        
        for row in results:
            avg_days = f"{row['avg_completion_days']:.1f}" if row['avg_completion_days'] else 'N/A'
            status_color = {
                'Closed': 'green',
                'DRAFT': 'yellow',
                'In Progress': 'blue',
                'To Do': 'red'
            }.get(row['status'], 'white')
            
            table.add_row(
                row['assignee_name'] or 'Unknown',
                row['assignee_email'] or 'Unknown',
                f"[{status_color}]{row['status']}[/{status_color}]",
                str(row['ticket_count']),
                avg_days
            )
        
        return table
    
    def get_commit_patterns_by_developer(self):
        """Analyze commit patterns by developer (team-filtered)"""
        query = """
        SELECT 
            gc.author_name,
            gc.author_email,
            COUNT(*) as total_commits,
            COUNT(CASE WHEN gc.message LIKE '%merge%' OR gc.message LIKE '%Merge%' THEN 1 END) as merge_commits,
            COUNT(CASE WHEN gc.message LIKE '%fix%' OR gc.message LIKE '%Fix%' THEN 1 END) as fix_commits,
            COUNT(CASE WHEN gc.message LIKE '%feat%' OR gc.message LIKE '%feature%' THEN 1 END) as feature_commits,
            MIN(gc.date) as first_commit,
            MAX(gc.date) as last_commit
        FROM git_commits gc
        WHERE EXISTS (
            SELECT 1 FROM team_members tm 
            WHERE gc.author_email = tm.email_address 
               OR gc.author_name = tm.display_name
        )
        GROUP BY gc.author_email
        ORDER BY total_commits DESC;
        """
        
        cursor = self.conn.execute(query)
        results = cursor.fetchall()
        
        table = Table(title="Commit Patterns by Developer")
        table.add_column("Developer", style="cyan")
        table.add_column("Email", style="blue")
        table.add_column("Total", justify="right", style="green")
        table.add_column("Merges", justify="right", style="yellow")
        table.add_column("Fixes", justify="right", style="red")
        table.add_column("Features", justify="right", style="magenta")
        table.add_column("First Commit", style="dim")
        table.add_column("Last Commit", style="dim")
        
        for row in results:
            table.add_row(
                row['author_name'] or 'Unknown',
                row['author_email'] or 'Unknown',
                str(row['total_commits']),
                str(row['merge_commits']),
                str(row['fix_commits']),
                str(row['feature_commits']),
                row['first_commit'][:10] if row['first_commit'] else 'N/A',
                row['last_commit'][:10] if row['last_commit'] else 'N/A'
            )
        
        return table
    
    def get_jira_git_correlation_report(self):
        """Generate report showing correlation between Jira tickets and Git activity"""
        query = """
        SELECT 
            jira_id,
            summary,
            assignee_name,
            assignee_email,
            status,
            jira_created,
            jira_updated,
            related_commits,
            related_pull_requests,
            related_merges,
            commit_authors,
            first_commit_date,
            last_commit_date
        FROM jira_git_correlation
        WHERE (related_commits > 0 OR related_pull_requests > 0 OR related_merges > 0)
        ORDER BY related_commits DESC, related_pull_requests DESC;
        """
        
        cursor = self.conn.execute(query)
        results = cursor.fetchall()
        
        table = Table(title="Jira-Git Correlation Report")
        table.add_column("Jira ID", style="cyan")
        table.add_column("Summary", style="white", max_width=40)
        table.add_column("Assignee", style="blue")
        table.add_column("Status", style="yellow")
        table.add_column("Commits", justify="right", style="green")
        table.add_column("PRs", justify="right", style="magenta")
        table.add_column("Merges", justify="right", style="red")
        table.add_column("Commit Authors", style="dim", max_width=30)
        
        for row in results:
            status_color = {
                'Closed': 'green',
                'DRAFT': 'yellow',
                'In Progress': 'blue',
                'To Do': 'red'
            }.get(row['status'], 'white')
            
            table.add_row(
                row['jira_id'],
                row['summary'][:37] + "..." if len(row['summary']) > 40 else row['summary'],
                row['assignee_name'] or 'Unknown',
                f"[{status_color}]{row['status']}[/{status_color}]",
                str(row['related_commits']),
                str(row['related_pull_requests']),
                str(row['related_merges']),
                (row['commit_authors'] or 'None')[:27] + "..." if row['commit_authors'] and len(row['commit_authors']) > 30 else (row['commit_authors'] or 'None')
            )
        
        return table
    
    def generate_summary_statistics(self):
        """Generate overall summary statistics"""
        stats = {}
        
        # Total counts
        cursor = self.conn.execute("SELECT COUNT(*) FROM iotmi_3p_issues")
        stats['total_jira_tickets'] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM git_commits")
        stats['total_commits'] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM codecommit_pull_requests")
        stats['total_pull_requests'] = cursor.fetchone()[0]
        
        cursor = self.conn.execute("SELECT COUNT(*) FROM codecommit_merges")
        stats['total_merges'] = cursor.fetchone()[0]
        
        # Active developers
        cursor = self.conn.execute("SELECT COUNT(DISTINCT author_email) FROM git_commits WHERE author_email IS NOT NULL")
        stats['active_developers'] = cursor.fetchone()[0]
        
        # Jira status distribution
        cursor = self.conn.execute("""
            SELECT json_extract(status, '$.name') as status, COUNT(*) as count 
            FROM iotmi_3p_issues 
            GROUP BY status 
            ORDER BY count DESC
        """)
        stats['jira_status_distribution'] = cursor.fetchall()
        
        return stats
    
    def display_summary_panel(self):
        """Display a summary panel with key statistics"""
        stats = self.generate_summary_statistics()
        
        summary_text = f"""
[bold cyan]📊 SDM Tools - Data Summary[/bold cyan]

[yellow]📋 Jira Tickets:[/yellow] {stats['total_jira_tickets']}
[green]💻 Git Commits:[/green] {stats['total_commits']}
[blue]🔄 Pull Requests:[/blue] {stats['total_pull_requests']}
[magenta]🔀 Merges:[/magenta] {stats['total_merges']}
[cyan]👥 Active Developers:[/cyan] {stats['active_developers']}

[bold yellow]Jira Status Distribution:[/bold yellow]
"""
        
        for status_row in stats['jira_status_distribution']:
            status = status_row[0] or 'Unknown'
            count = status_row[1]
            summary_text += f"  • {status}: {count}\n"
        
        panel = Panel(summary_text, title="Project Overview", border_style="bright_blue")
        console.print(panel)
        
        return panel


def generate_all_reports():
    """Generate all available reports"""
    reporter = SDMReporter()
    
    try:
        # Create database views
        console.print("[bold yellow]Creating database views...[/bold yellow]")
        reporter.create_developer_activity_view()
        reporter.create_jira_git_correlation_view()
        
        # Display summary
        console.print("\n")
        reporter.display_summary_panel()
        
        # Generate and display reports
        console.print("\n" + "="*80)
        console.print(reporter.get_developer_productivity_report())
        
        console.print("\n" + "="*80)
        console.print(reporter.get_jira_completion_analysis())
        
        console.print("\n" + "="*80)
        console.print(reporter.get_commit_patterns_by_developer())
        
        console.print("\n" + "="*80)
        console.print(reporter.get_jira_git_correlation_report())
        
        console.print("\n[bold green]✅ All reports generated successfully![/bold green]")
        
    except Exception as e:
        console.print(f"[bold red]❌ Error generating reports: {e}[/bold red]")
    finally:
        reporter.close()


if __name__ == "__main__":
    generate_all_reports()
