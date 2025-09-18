#!/usr/bin/env python3
"""
Export Developer Analytics Data to JSON for SPA consumption
"""
import json
import os
from datetime import datetime
from sdm_tools.analytics import DeveloperAnalytics
from rich.console import Console

console = Console()


def export_developer_data_to_json(output_file: str = "developer_data.json"):
    """Export developer analytics data to JSON file for SPA consumption"""
    analytics = DeveloperAnalytics()

    try:
        console.print(
            "[bold blue]🔍 Generating developer analytics data...[/bold blue]")

        # Generate fresh metrics
        metrics = analytics.generate_developer_metrics()
        if not metrics:
            console.print(
                "[red]No developer data found. Please ensure you have both Git commits and Jira data.[/red]")
            return None

        # Generate insights
        insights = analytics.generate_team_insights(metrics)

        # Create comprehensive JSON structure for SPA
        export_data = {
            "metadata": {
                "export_date": datetime.now().isoformat(),
                "total_developers": len(metrics),
                "data_version": "1.0"
            },
            "team_summary": {
                "total_commits": sum(m.commit_count for m in metrics),
                "total_issues_resolved": sum(m.issues_resolved for m in metrics),
                "total_issues_assigned": sum(m.issues_assigned for m in metrics),
                "total_story_points": sum(m.story_points_completed for m in metrics),
                "avg_productivity_score": round(sum(m.productivity_score for m in metrics) / len(metrics), 2),
                "avg_collaboration_score": round(sum(m.collaboration_score for m in metrics) / len(metrics), 2),
                "avg_code_quality_score": round(sum(m.code_quality_score for m in metrics) / len(metrics), 2)
            },
            "developers": []
        }

        # Add individual developer data
        for i, metric in enumerate(metrics, 1):
            developer_data = {
                "id": i,
                "name": metric.name,
                "email": metric.email,
                "rank": i,
                "avatar": f"https://ui-avatars.com/api/?name={metric.name.replace(' ', '+')}&background=random&color=fff&size=128",
                "commit_activity": {
                    "total_commits": metric.commit_count,
                    "commit_frequency": round(metric.commit_frequency, 3),
                    "avg_commits_per_day": round(metric.avg_commits_per_day, 2),
                    "peak_commit_day": metric.peak_commit_day,
                    "peak_commit_hour": metric.peak_commit_hour
                },
                "issue_management": {
                    "issues_created": metric.issues_created,
                    "issues_assigned": metric.issues_assigned,
                    "issues_resolved": metric.issues_resolved,
                    "avg_resolution_time": round(metric.avg_resolution_time, 1),
                    "story_points_completed": metric.story_points_completed,
                    "resolution_rate": round((metric.issues_resolved / max(metric.issues_assigned, 1)) * 100, 1)
                },
                "performance_scores": {
                    "productivity_score": round(metric.productivity_score, 1),
                    "collaboration_score": round(metric.collaboration_score, 1),
                    "code_quality_score": round(metric.code_quality_score, 1),
                    "overall_score": round((metric.productivity_score + metric.collaboration_score + metric.code_quality_score) / 3, 1)
                },
                "badges": _generate_badges(metric),
                "insights": _generate_developer_insights(metric)
            }
            export_data["developers"].append(developer_data)

        # Add team insights
        export_data["team_insights"] = {
            "top_performers": [
                {
                    "name": m.name,
                    "productivity_score": round(m.productivity_score, 1)
                }
                for m in metrics[:5]
            ],
            "collaboration_leaders": [
                {
                    "name": m.name,
                    "collaboration_score": round(m.collaboration_score, 1)
                }
                for m in sorted(metrics, key=lambda x: x.collaboration_score, reverse=True)[:3]
            ],
            "quality_champions": [
                {
                    "name": m.name,
                    "code_quality_score": round(m.code_quality_score, 1)
                }
                for m in sorted(metrics, key=lambda x: x.code_quality_score, reverse=True)[:3]
            ],
            "recommendations": insights.get('recommendations', [])
        }

        # Write to JSON file
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        console.print(
            f"[green]✅ Successfully exported data for {len(metrics)} developers to {output_file}[/green]")
        console.print(f"[cyan]📊 Team Summary:[/cyan]")
        console.print(
            f"  • Total Commits: {export_data['team_summary']['total_commits']:,}")
        console.print(
            f"  • Issues Resolved: {export_data['team_summary']['total_issues_resolved']}")
        console.print(
            f"  • Avg Productivity: {export_data['team_summary']['avg_productivity_score']}/100")

        return output_file

    except Exception as e:
        console.print(f"[red]❌ Error exporting data: {e}[/red]")
        return None
    finally:
        analytics.close()


def _generate_badges(metric):
    """Generate achievement badges for a developer"""
    badges = []

    # Productivity badges
    if metric.productivity_score >= 80:
        badges.append({"name": "High Performer",
                      "color": "green", "icon": "🚀"})
    elif metric.productivity_score >= 60:
        badges.append({"name": "Solid Contributor",
                      "color": "blue", "icon": "💪"})

    # Collaboration badges
    if metric.collaboration_score >= 70:
        badges.append({"name": "Team Player", "color": "purple", "icon": "🤝"})

    # Quality badges
    if metric.code_quality_score >= 75:
        badges.append({"name": "Quality Champion",
                      "color": "yellow", "icon": "⭐"})

    # Commit frequency badges
    if metric.commit_frequency >= 1.0:
        badges.append({"name": "Daily Committer",
                      "color": "orange", "icon": "📅"})

    # Issue resolution badges
    if metric.issues_resolved >= 10:
        badges.append({"name": "Problem Solver", "color": "red", "icon": "🔧"})

    # Story points badges
    if metric.story_points_completed >= 50:
        badges.append({"name": "Story Master", "color": "indigo", "icon": "📚"})

    return badges


def _generate_developer_insights(metric):
    """Generate personalized insights for a developer"""
    insights = []

    # Productivity insights
    if metric.productivity_score >= 80:
        insights.append(
            "Exceptional productivity levels - keep up the great work!")
    elif metric.productivity_score < 40:
        insights.append(
            "Consider focusing on increasing commit frequency and issue resolution.")

    # Collaboration insights
    if metric.collaboration_score >= 70:
        insights.append(
            "Strong collaboration skills evident through merge commits and team engagement.")
    elif metric.collaboration_score < 40:
        insights.append(
            "Consider participating more in code reviews and team discussions.")

    # Work pattern insights
    if metric.peak_commit_hour < 9:
        insights.append("Early bird developer - most active in morning hours.")
    elif metric.peak_commit_hour > 17:
        insights.append(
            "Night owl developer - most productive in evening hours.")

    # Issue resolution insights
    if metric.avg_resolution_time > 0:
        if metric.avg_resolution_time < 7:
            insights.append(
                "Quick issue resolution - excellent turnaround time!")
        elif metric.avg_resolution_time > 14:
            insights.append(
                "Consider breaking down complex issues into smaller tasks.")

    return insights


if __name__ == "__main__":
    export_developer_data_to_json()
