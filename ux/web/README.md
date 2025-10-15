# Dashboard Templates

This directory contains HTML dashboard templates that are converted into standalone reports.

## Template Files

1. **developer-activity-dashboard.html**
   - Shows developer activity by sprint and last 3 days
   - Data source: `data/developer_activity.json`
   - Output: `dist/developer-activity-dashboard.html`

2. **developer-comparison-dashboard.html**
   - Individual developer performance vs team benchmarks
   - Data sources: `data/team_sprint_stats.json` + `data/developer_activity.json`
   - Output: `dist/developer-comparison-dashboard.html`

3. **team-sprint-dashboard.html**
   - Team sprint analytics with multiple views
   - Data source: `data/team_sprint_stats.json`
   - Output: `dist/team-sprint-dashboard.html`

4. **team-sprint-kpi-dashboard.html**
   - Team KPI metrics and performance indicators
   - Data source: `data/team_sprint_stats.json`
   - Output: `dist/team-sprint-kpi-dashboard.html`

## Naming Convention

- Templates: `{scope}-{type}-dashboard.html`
  - scope: `developer` or `team`
  - type: describes the dashboard focus (activity, comparison, sprint, kpi)

- Outputs: Same name in `dist/` folder as standalone files

## Generation Process

Run option 5 in the CLI to generate standalone HTML files that:
- Embed CSS from `shared-dashboard-styles.css`
- Embed JSON data directly in the HTML
- Can be opened directly in any browser without external dependencies
