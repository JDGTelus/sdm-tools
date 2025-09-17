"""
Developer Performance Analytics Module
Provides industry-standard insights into developer performance using Git commits and Jira data
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from collections import defaultdict, Counter
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.progress import track
import statistics

from .config import DB_NAME
from .team_filter import TeamMemberExtractor

console = Console()


@dataclass
class DeveloperMetrics:
    """Data class to hold developer performance metrics"""
    name: str
    email: str
    commit_count: int
    commit_frequency: float  # commits per day
    avg_commits_per_day: float
    peak_commit_day: str
    peak_commit_hour: int
    issues_created: int
    issues_assigned: int
    issues_resolved: int
    avg_resolution_time: float  # days
    story_points_completed: float
    productivity_score: float
    collaboration_score: float
    code_quality_score: float


class DeveloperAnalytics:
    """Main analytics engine for developer performance insights"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_NAME
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.team_extractor = TeamMemberExtractor(self.db_path)
        
    def close(self):
        """Close database connections"""
        self.conn.close()
        self.team_extractor.close()
        
    def get_commit_metrics(self) -> Dict[str, Dict]:
        """Analyze Git commit patterns and metrics"""
        query = """
        SELECT author_name, author_email, date, message, hash
        FROM git_commits 
        ORDER BY date
        """
        
        cursor = self.conn.execute(query)
        commits = cursor.fetchall()
        
        developer_commits = defaultdict(list)
        
        for commit in commits:
            key = (commit['author_name'], commit['author_email'])
            try:
                # Parse different date formats
                date_str = commit['date']
                if 'T' in date_str:
                    commit_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    # Handle git log format: "Thu Sep 11 15:24:43 2025 +0000"
                    # Try different timezone formats
                    try:
                        commit_date = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y %z")
                    except ValueError:
                        # Try without timezone
                        try:
                            commit_date = datetime.strptime(date_str.split(' +')[0].split(' -')[0], "%a %b %d %H:%M:%S %Y")
                        except ValueError:
                            # Skip this commit if we can't parse the date
                            continue
                
                developer_commits[key].append({
                    'date': commit_date,
                    'message': commit['message'],
                    'hash': commit['hash']
                })
            except (ValueError, TypeError) as e:
                console.print(f"[yellow]Warning: Could not parse date {date_str}: {e}[/yellow]")
                continue
        
        metrics = {}
        for (name, email), commits in developer_commits.items():
            if not commits:
                continue
                
            # Sort commits by date
            commits.sort(key=lambda x: x['date'])
            
            # Calculate time span
            first_commit = commits[0]['date']
            last_commit = commits[-1]['date']
            days_active = max(1, (last_commit - first_commit).days + 1)
            
            # Commit frequency analysis
            commit_frequency = len(commits) / days_active
            
            # Day of week analysis
            day_counts = Counter(commit['date'].strftime('%A') for commit in commits)
            peak_day = day_counts.most_common(1)[0][0] if day_counts else 'Unknown'
            
            # Hour of day analysis
            hour_counts = Counter(commit['date'].hour for commit in commits)
            peak_hour = hour_counts.most_common(1)[0][0] if hour_counts else 0
            
            # Merge commit analysis
            merge_commits = [c for c in commits if 'merge' in c['message'].lower()]
            merge_ratio = len(merge_commits) / len(commits) if commits else 0
            
            metrics[(name, email)] = {
                'total_commits': len(commits),
                'days_active': days_active,
                'commit_frequency': commit_frequency,
                'avg_commits_per_day': len(commits) / days_active,
                'peak_commit_day': peak_day,
                'peak_commit_hour': peak_hour,
                'merge_commits': len(merge_commits),
                'merge_ratio': merge_ratio,
                'first_commit': first_commit,
                'last_commit': last_commit,
                'commits': commits
            }
            
        return metrics
    
    def get_jira_metrics(self) -> Dict[str, Dict]:
        """Analyze Jira issue patterns and metrics"""
        # Get issues created by developers
        created_query = """
        SELECT creator, created, status, priority, summary, assignee, updated, customfield_10026
        FROM iotmi_3p_issues 
        WHERE creator IS NOT NULL AND creator != 'null'
        """
        
        # Get issues assigned to developers
        assigned_query = """
        SELECT assignee, created, status, priority, summary, updated, customfield_10026
        FROM iotmi_3p_issues 
        WHERE assignee IS NOT NULL AND assignee != 'null'
        """
        
        creator_cursor = self.conn.execute(created_query)
        created_issues = creator_cursor.fetchall()
        
        assigned_cursor = self.conn.execute(assigned_query)
        assigned_issues = assigned_cursor.fetchall()
        
        metrics = defaultdict(lambda: {
            'issues_created': 0,
            'issues_assigned': 0,
            'issues_resolved': 0,
            'total_story_points': 0,
            'resolution_times': [],
            'issue_types': Counter(),
            'priority_distribution': Counter()
        })
        
        # Process created issues
        for issue in created_issues:
            creator_info = self._parse_user_field(issue['creator'])
            if not creator_info:
                continue
                
            display_name = creator_info.get('displayName', 'Unknown')
            email_address = creator_info.get('emailAddress', '')
            key = (display_name, email_address)
            metrics[key]['issues_created'] += 1
            
            # Story points (customfield_10026 appears to be story points)
            story_points = self._parse_story_points(issue['customfield_10026'])
            if story_points:
                metrics[key]['total_story_points'] += story_points
            
            # Priority distribution
            priority = self._parse_priority(issue['priority'])
            if priority:
                metrics[key]['priority_distribution'][priority] += 1
        
        # Process assigned issues
        for issue in assigned_issues:
            assignee_info = self._parse_user_field(issue['assignee'])
            if not assignee_info:
                continue
                
            display_name = assignee_info.get('displayName', 'Unknown')
            email_address = assignee_info.get('emailAddress', '')
            key = (display_name, email_address)
            metrics[key]['issues_assigned'] += 1
            
            # Check if resolved
            status_info = self._parse_status(issue['status'])
            if status_info and self._is_resolved_status(status_info['name']):
                metrics[key]['issues_resolved'] += 1
                
                # Calculate resolution time
                resolution_time = self._calculate_resolution_time(
                    issue['created'], issue['updated']
                )
                if resolution_time:
                    metrics[key]['resolution_times'].append(resolution_time)
        
        # Calculate averages
        for key, data in metrics.items():
            if data['resolution_times']:
                data['avg_resolution_time'] = statistics.mean(data['resolution_times'])
            else:
                data['avg_resolution_time'] = 0
                
        return dict(metrics)
    
    def _parse_user_field(self, user_field: str) -> Optional[Dict]:
        """Parse user field from Jira data"""
        if not user_field or user_field == 'null':
            return None
            
        try:
            # Try JSON first
            try:
                return json.loads(user_field)
            except json.JSONDecodeError:
                # Try eval for Python dict strings
                return eval(user_field)
        except:
            return None
    
    def _parse_story_points(self, points_field: str) -> Optional[float]:
        """Parse story points field"""
        if not points_field or points_field == 'null':
            return None
        try:
            return float(points_field)
        except (ValueError, TypeError):
            return None
    
    def _parse_priority(self, priority_field: str) -> Optional[str]:
        """Parse priority field"""
        if not priority_field or priority_field == 'null':
            return None
        try:
            priority_data = json.loads(priority_field) if isinstance(priority_field, str) else priority_field
            return priority_data.get('name', 'Unknown')
        except:
            return 'Unknown'
    
    def _parse_status(self, status_field: str) -> Optional[Dict]:
        """Parse status field"""
        if not status_field or status_field == 'null':
            return None
        try:
            return json.loads(status_field) if isinstance(status_field, str) else status_field
        except:
            return None
    
    def _is_resolved_status(self, status_name: str) -> bool:
        """Check if status indicates resolution"""
        resolved_statuses = {
            'done', 'closed', 'resolved', 'completed', 'finished',
            'deployed', 'released', 'verified', 'accepted'
        }
        return status_name.lower() in resolved_statuses
    
    def _calculate_resolution_time(self, created: str, updated: str) -> Optional[float]:
        """Calculate resolution time in days"""
        try:
            created_date = datetime.fromisoformat(created.replace('Z', '+00:00'))
            updated_date = datetime.fromisoformat(updated.replace('Z', '+00:00'))
            return (updated_date - created_date).total_seconds() / 86400  # days
        except:
            return None
    
    def calculate_productivity_score(self, commit_metrics: Dict, jira_metrics: Dict) -> float:
        """Calculate overall productivity score (0-100)"""
        # Weighted scoring based on multiple factors
        commit_score = min(commit_metrics.get('commit_frequency', 0) * 10, 30)  # Max 30 points
        resolution_score = min(jira_metrics.get('issues_resolved', 0) * 5, 25)  # Max 25 points
        story_points_score = min(jira_metrics.get('total_story_points', 0) * 2, 25)  # Max 25 points
        consistency_score = min(commit_metrics.get('days_active', 0) / 30 * 20, 20)  # Max 20 points
        
        return min(commit_score + resolution_score + story_points_score + consistency_score, 100)
    
    def calculate_collaboration_score(self, commit_metrics: Dict, jira_metrics: Dict) -> float:
        """Calculate collaboration score based on merge commits and issue interactions"""
        merge_ratio = commit_metrics.get('merge_ratio', 0)
        issues_created = jira_metrics.get('issues_created', 0)
        
        # Higher merge ratio indicates more collaboration
        merge_score = min(merge_ratio * 50, 50)  # Max 50 points
        
        # Creating issues shows engagement with team processes
        creation_score = min(issues_created * 5, 50)  # Max 50 points
        
        return min(merge_score + creation_score, 100)
    
    def calculate_code_quality_score(self, commit_metrics: Dict) -> float:
        """Calculate code quality score based on commit patterns"""
        commits = commit_metrics.get('commits', [])
        if not commits:
            return 0
        
        # Analyze commit message quality
        quality_indicators = 0
        total_commits = len(commits)
        
        for commit in commits:
            message = commit['message'].lower()
            
            # Good practices
            if any(keyword in message for keyword in ['fix', 'bug', 'issue']):
                quality_indicators += 1
            if any(keyword in message for keyword in ['test', 'spec', 'coverage']):
                quality_indicators += 1
            if any(keyword in message for keyword in ['refactor', 'clean', 'optimize']):
                quality_indicators += 1
            if len(commit['message']) > 20:  # Descriptive messages
                quality_indicators += 1
        
        # Calculate ratio and scale to 100
        quality_ratio = quality_indicators / (total_commits * 4) if total_commits > 0 else 0
        return min(quality_ratio * 100, 100)
    
    def generate_developer_metrics(self) -> List[DeveloperMetrics]:
        """Generate comprehensive developer metrics"""
        console.print("[bold blue]🔍 Analyzing developer performance...[/bold blue]")
        
        commit_metrics = self.get_commit_metrics()
        jira_metrics = self.get_jira_metrics()
        
        # Get all unique developers
        all_developers = set()
        all_developers.update(commit_metrics.keys())
        all_developers.update(jira_metrics.keys())
        
        developer_metrics = []
        
        for name, email in track(all_developers, description="Processing developers..."):
            commit_data = commit_metrics.get((name, email), {})
            jira_data = jira_metrics.get((name, email), {})
            
            # Calculate scores
            productivity_score = self.calculate_productivity_score(commit_data, jira_data)
            collaboration_score = self.calculate_collaboration_score(commit_data, jira_data)
            code_quality_score = self.calculate_code_quality_score(commit_data)
            
            metrics = DeveloperMetrics(
                name=name,
                email=email,
                commit_count=commit_data.get('total_commits', 0),
                commit_frequency=commit_data.get('commit_frequency', 0),
                avg_commits_per_day=commit_data.get('avg_commits_per_day', 0),
                peak_commit_day=commit_data.get('peak_commit_day', 'Unknown'),
                peak_commit_hour=commit_data.get('peak_commit_hour', 0),
                issues_created=jira_data.get('issues_created', 0),
                issues_assigned=jira_data.get('issues_assigned', 0),
                issues_resolved=jira_data.get('issues_resolved', 0),
                avg_resolution_time=jira_data.get('avg_resolution_time', 0),
                story_points_completed=jira_data.get('total_story_points', 0),
                productivity_score=productivity_score,
                collaboration_score=collaboration_score,
                code_quality_score=code_quality_score
            )
            
            developer_metrics.append(metrics)
        
        # Sort by productivity score
        developer_metrics.sort(key=lambda x: x.productivity_score, reverse=True)
        
        return developer_metrics
    
    def display_performance_summary(self, metrics: List[DeveloperMetrics]):
        """Display a comprehensive performance summary"""
        if not metrics:
            console.print("[red]No developer metrics available.[/red]")
            return
        
        # Overall statistics
        total_commits = sum(m.commit_count for m in metrics)
        total_issues_resolved = sum(m.issues_resolved for m in metrics)
        avg_productivity = statistics.mean(m.productivity_score for m in metrics)
        avg_collaboration = statistics.mean(m.collaboration_score for m in metrics)
        avg_quality = statistics.mean(m.code_quality_score for m in metrics)
        
        # Create summary panel
        summary_text = f"""
[bold cyan]📊 Team Performance Overview[/bold cyan]

[green]Total Developers:[/green] {len(metrics)}
[green]Total Commits:[/green] {total_commits:,}
[green]Total Issues Resolved:[/green] {total_issues_resolved}
[green]Average Productivity Score:[/green] {avg_productivity:.1f}/100
[green]Average Collaboration Score:[/green] {avg_collaboration:.1f}/100
[green]Average Code Quality Score:[/green] {avg_quality:.1f}/100
        """
        
        console.print(Panel(summary_text, title="Team Summary", border_style="blue"))
        
        # Top performers table
        console.print("\n[bold yellow]🏆 Top Performers by Productivity Score[/bold yellow]")
        
        table = Table(show_header=True, header_style="bold green")
        table.add_column("Rank", style="cyan", width=6)
        table.add_column("Developer", style="white", width=25)
        table.add_column("Commits", justify="right", style="blue")
        table.add_column("Issues Resolved", justify="right", style="green")
        table.add_column("Productivity", justify="right", style="yellow")
        table.add_column("Collaboration", justify="right", style="magenta")
        table.add_column("Code Quality", justify="right", style="cyan")
        
        for i, metric in enumerate(metrics[:10], 1):  # Top 10
            table.add_row(
                f"#{i}",
                f"{metric.name[:22]}..." if len(metric.name) > 25 else metric.name,
                str(metric.commit_count),
                str(metric.issues_resolved),
                f"{metric.productivity_score:.1f}",
                f"{metric.collaboration_score:.1f}",
                f"{metric.code_quality_score:.1f}"
            )
        
        console.print(table)
    
    def display_detailed_metrics(self, metrics: List[DeveloperMetrics]):
        """Display detailed metrics for each developer"""
        for metric in metrics:
            self._display_individual_developer(metric)
    
    def _display_individual_developer(self, metric: DeveloperMetrics):
        """Display detailed metrics for a single developer"""
        # Create detailed panel for each developer
        details = f"""
[bold cyan]👤 {metric.name}[/bold cyan]
[dim]{metric.email}[/dim]

[yellow]📈 Commit Activity:[/yellow]
  • Total Commits: {metric.commit_count}
  • Commits per Day: {metric.avg_commits_per_day:.2f}
  • Peak Day: {metric.peak_commit_day}
  • Peak Hour: {metric.peak_commit_hour}:00

[yellow]🎫 Issue Management:[/yellow]
  • Issues Created: {metric.issues_created}
  • Issues Assigned: {metric.issues_assigned}
  • Issues Resolved: {metric.issues_resolved}
  • Avg Resolution Time: {metric.avg_resolution_time:.1f} days
  • Story Points: {metric.story_points_completed}

[yellow]📊 Performance Scores:[/yellow]
  • Productivity: {metric.productivity_score:.1f}/100
  • Collaboration: {metric.collaboration_score:.1f}/100
  • Code Quality: {metric.code_quality_score:.1f}/100
        """
        
        # Color code based on productivity score
        border_color = "green" if metric.productivity_score >= 70 else "yellow" if metric.productivity_score >= 40 else "red"
        
        console.print(Panel(details, title=f"Developer Profile", border_style=border_color))
        console.print()
    
    def generate_team_insights(self, metrics: List[DeveloperMetrics]) -> Dict[str, Any]:
        """Generate actionable team insights"""
        if not metrics:
            return {}
        
        insights = {
            'top_performers': [],
            'improvement_candidates': [],
            'collaboration_leaders': [],
            'quality_champions': [],
            'workload_distribution': {},
            'recommendations': []
        }
        
        # Identify top performers (top 20%)
        top_20_percent = max(1, len(metrics) // 5)
        insights['top_performers'] = metrics[:top_20_percent]
        
        # Identify improvement candidates (bottom 20%)
        bottom_20_percent = max(1, len(metrics) // 5)
        insights['improvement_candidates'] = metrics[-bottom_20_percent:]
        
        # Collaboration leaders
        sorted_by_collaboration = sorted(metrics, key=lambda x: x.collaboration_score, reverse=True)
        insights['collaboration_leaders'] = sorted_by_collaboration[:3]
        
        # Quality champions
        sorted_by_quality = sorted(metrics, key=lambda x: x.code_quality_score, reverse=True)
        insights['quality_champions'] = sorted_by_quality[:3]
        
        # Workload analysis
        total_issues = sum(m.issues_assigned for m in metrics)
        for metric in metrics:
            if total_issues > 0:
                workload_percentage = (metric.issues_assigned / total_issues) * 100
                insights['workload_distribution'][metric.name] = workload_percentage
        
        # Generate recommendations
        insights['recommendations'] = self._generate_recommendations(metrics)
        
        return insights
    
    def _generate_recommendations(self, metrics: List[DeveloperMetrics]) -> List[str]:
        """Generate actionable recommendations based on metrics"""
        recommendations = []
        
        if not metrics:
            return recommendations
        
        # Analyze team patterns
        avg_productivity = statistics.mean(m.productivity_score for m in metrics)
        avg_collaboration = statistics.mean(m.collaboration_score for m in metrics)
        avg_quality = statistics.mean(m.code_quality_score for m in metrics)
        
        # Low productivity recommendations
        if avg_productivity < 50:
            recommendations.append("🔴 Team productivity is below average. Consider reviewing sprint planning and removing blockers.")
        
        # Collaboration recommendations
        if avg_collaboration < 40:
            recommendations.append("🤝 Low collaboration scores detected. Encourage pair programming and code reviews.")
        
        # Quality recommendations
        if avg_quality < 60:
            recommendations.append("🔧 Code quality scores need improvement. Implement commit message standards and code review processes.")
        
        # Workload distribution
        workloads = [m.issues_assigned for m in metrics if m.issues_assigned > 0]
        if workloads and statistics.stdev(workloads) > statistics.mean(workloads) * 0.5:
            recommendations.append("⚖️ Uneven workload distribution detected. Consider rebalancing task assignments.")
        
        # Resolution time analysis
        resolution_times = [m.avg_resolution_time for m in metrics if m.avg_resolution_time > 0]
        if resolution_times and statistics.mean(resolution_times) > 14:  # More than 2 weeks
            recommendations.append("⏰ High average resolution times. Review issue complexity and provide additional support.")
        
        # Commit frequency analysis
        commit_frequencies = [m.commit_frequency for m in metrics if m.commit_frequency > 0]
        if commit_frequencies and statistics.mean(commit_frequencies) < 0.5:  # Less than 0.5 commits per day
            recommendations.append("📝 Low commit frequency. Encourage smaller, more frequent commits.")
        
        return recommendations
    
    def display_team_insights(self, insights: Dict[str, Any]):
        """Display team insights and recommendations"""
        console.print("\n[bold blue]🔍 Team Insights & Recommendations[/bold blue]")
        
        # Top performers
        if insights.get('top_performers'):
            console.print("\n[bold green]🏆 Top Performers:[/bold green]")
            for performer in insights['top_performers']:
                console.print(f"  • {performer.name} (Score: {performer.productivity_score:.1f})")
        
        # Improvement candidates
        if insights.get('improvement_candidates'):
            console.print("\n[bold yellow]📈 Growth Opportunities:[/bold yellow]")
            for candidate in insights['improvement_candidates']:
                console.print(f"  • {candidate.name} (Score: {candidate.productivity_score:.1f})")
        
        # Collaboration leaders
        if insights.get('collaboration_leaders'):
            console.print("\n[bold magenta]🤝 Collaboration Leaders:[/bold magenta]")
            for leader in insights['collaboration_leaders']:
                console.print(f"  • {leader.name} (Score: {leader.collaboration_score:.1f})")
        
        # Quality champions
        if insights.get('quality_champions'):
            console.print("\n[bold cyan]🔧 Quality Champions:[/bold cyan]")
            for champion in insights['quality_champions']:
                console.print(f"  • {champion.name} (Score: {champion.code_quality_score:.1f})")
        
        # Recommendations
        if insights.get('recommendations'):
            console.print("\n[bold red]💡 Recommendations:[/bold red]")
            for rec in insights['recommendations']:
                console.print(f"  {rec}")
    
    def export_metrics_to_db(self, metrics: List[DeveloperMetrics]):
        """Export calculated metrics to database for persistence"""
        # Create analytics table
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS developer_analytics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            analysis_date TEXT,
            developer_name TEXT,
            developer_email TEXT,
            commit_count INTEGER,
            commit_frequency REAL,
            avg_commits_per_day REAL,
            peak_commit_day TEXT,
            peak_commit_hour INTEGER,
            issues_created INTEGER,
            issues_assigned INTEGER,
            issues_resolved INTEGER,
            avg_resolution_time REAL,
            story_points_completed REAL,
            productivity_score REAL,
            collaboration_score REAL,
            code_quality_score REAL,
            UNIQUE(analysis_date, developer_email)
        )
        """
        
        self.conn.execute(create_table_sql)
        
        # Insert metrics
        analysis_date = datetime.now().isoformat()
        
        for metric in metrics:
            insert_sql = """
            INSERT OR REPLACE INTO developer_analytics (
                analysis_date, developer_name, developer_email, commit_count,
                commit_frequency, avg_commits_per_day, peak_commit_day, peak_commit_hour,
                issues_created, issues_assigned, issues_resolved, avg_resolution_time,
                story_points_completed, productivity_score, collaboration_score, code_quality_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            
            self.conn.execute(insert_sql, (
                analysis_date, metric.name, metric.email, metric.commit_count,
                metric.commit_frequency, metric.avg_commits_per_day, metric.peak_commit_day,
                metric.peak_commit_hour, metric.issues_created, metric.issues_assigned,
                metric.issues_resolved, metric.avg_resolution_time, metric.story_points_completed,
                metric.productivity_score, metric.collaboration_score, metric.code_quality_score
            ))
        
        self.conn.commit()
        console.print(f"[green]✓ Exported {len(metrics)} developer metrics to database[/green]")


def run_analytics_report():
    """Main function to run comprehensive analytics report"""
    analytics = DeveloperAnalytics()
    
    try:
        # Generate metrics
        metrics = analytics.generate_developer_metrics()
        
        if not metrics:
            console.print("[red]No developer data found. Please ensure you have both Git commits and Jira data.[/red]")
            return
        
        # Display summary
        analytics.display_performance_summary(metrics)
        
        # Generate and display insights
        insights = analytics.generate_team_insights(metrics)
        analytics.display_team_insights(insights)
        
        # Ask if user wants detailed view
        console.print("\n[bold yellow]Would you like to see detailed metrics for each developer? (y/n)[/bold yellow]")
        if input().lower().startswith('y'):
            analytics.display_detailed_metrics(metrics)
        
        # Export to database
        analytics.export_metrics_to_db(metrics)
        
        console.print("\n[bold green]✅ Analytics report completed![/bold green]")
        
    finally:
        analytics.close()


if __name__ == "__main__":
    run_analytics_report()
