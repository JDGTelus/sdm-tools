# SDM-Tools

SDM-Tools is a comprehensive command-line interface (CLI) tool designed for Software Developer Managers (SDMs) to manage and analyze their team's Jira tasks and repository commits. The tool provides customized insights and actions, making it easier to track and manage issues, backlog, sprint planning, commit history, and generate interactive HTML dashboards.

## Features

### Core Functionality
- **Jira Integration**: Identify active developers working on Jira stories or bugs
- **Issue Management**: Store and display Jira issues with customizable columns
- **Commit Tracking**: Fetch and store commit information from the repository
- **Data Backup**: Automatic backup of existing data files with timestamps
- **Pagination**: Display large datasets with colorful, paginated output

### Advanced Analytics
- **Sprint Analytics**: Generate comprehensive sprint-based team statistics in JSON format
- **Developer Activity Tracking**: Monitor individual developer activity across sprints and recent periods
- **Story Points Tracking**: Monitor story points closed by developers across sprints
- **Issue Code Extraction**: Automatically extract and display issue codes from Jira data
- **Sprint Progress Tracking**: Track sprint completion rates and developer contributions
- **Commit Integration**: Align git commit activity with sprint periods
- **Last 3 Days Activity**: Real-time tracking of recent developer activity

### Interactive Dashboards
- **Self-Sufficient HTML Dashboards**: Generate standalone HTML files with embedded data and styles
- **Multiple Dashboard Types**:
  - **Sprint Analytics Dashboard**: Sprint-focused activity with story points tracking
  - **KPI Dashboard**: Key performance indicators and team metrics
  - **Developer Activity Dashboard**: Individual developer activity with sprint breakdowns and recent activity
- **Responsive Design**: Modern, mobile-friendly interface using TailwindCSS
- **Real-time Data**: Embedded JSON data for instant loading without external dependencies
- **Interactive Charts**: Pie charts and bar charts for visual data representation

## Setup

### Prerequisites

- Python 3.6 or higher
- Jira account with API access
- Local repository with commit history

### Jira API Token

To generate a Jira API token:
1. Log in to your Jira account.
2. Navigate to your account settings.
3. Find the "API tokens" section.
4. Generate a new API token and copy it.
5. Set the `JIRA_API_TOKEN` environment variable with the copied token.

### Virtual Environment Setup

1. **Create a virtual environment**:
   ```bash
   python3 -m venv .venv
   ```
2. **Activate the virtual environment**:
   - On macOS/Linux:
     ```bash
     source .venv/bin/activate
     ```
   - On Windows:
     ```bash
     .venv\Scripts\activate
     ```
3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Environment Variables

Set the following environment variables for configuration:

#### Required Variables
- `JIRA_URL`: Base URL for Jira API (e.g., `https://your-jira-domain.atlassian.net`)
- `JIRA_API_TOKEN`: API token for authentication
- `JIRA_EMAIL`: Email associated with the Jira account
- `JQL_QUERY`: JQL query to filter issues (e.g., `project = "SET" AND component = "IOTMI 3P Connector"`)
- `DISPLAY_COLUMNS`: Comma-separated list of columns to display (e.g., `id,summary,description,assignee,reporter,status`)
- `REPO_PATH`: Path to the local repository (e.g., `/path/to/repo`)

#### Optional Variables (with defaults)
- `DB_NAME`: Name of the SQLite database file (default: `data/sdm_tools.db`)
- `TABLE_NAME`: Name of the table to store issues (default: `iotmi_3p_issues`)
- `EXCLUDED_EMAILS`: Comma-separated list of email addresses to exclude from analytics (default: empty)

#### Additional Variables
- `REPO_NAME`: Name of the repository for reference (e.g., `your-repo-name`)

### Example Configuration

Create a `.env` file in the project root:

```bash
#!/bin/bash
export JIRA_URL='https://your-jira-domain.atlassian.net'
export JIRA_API_TOKEN='your-api-token'
export JIRA_EMAIL='your-email@example.com'
export JQL_QUERY='project = "SET" AND component = "IOTMI 3P Connector" AND type = "Story"'
export DISPLAY_COLUMNS='id,summary,description,assignee,reporter,status'
export DB_NAME='sdm_tools.db'
export TABLE_NAME='iotmi_3p_issues'
export REPO_PATH='/path/to/repo'
export REPO_NAME='your-repo-name'
export EXCLUDED_EMAILS='bot@example.com,automated@example.com'
```

## Usage

### Running the CLI Tool

1. **Load environment variables**:
   ```bash
   set -a; source .env; set +a
   ```
2. **Run the CLI tool**:
   ```bash
   python -m sdm_tools.cli
   ```

### Menu Options

The CLI provides the following options:

1. **Manage Jira issues (get/update/display)**
   - Fetch issues from Jira using the configured JQL query
   - Update existing issue data
   - Display issues with customizable columns and pagination

2. **Manage git commits (get/update/display)**
   - Fetch commit information from the local repository
   - Update commit data since the earliest Jira ticket date
   - Display commits with author information and pagination

3. **Team sprint analytics JSON (update/display)**
   - Generate comprehensive sprint-based statistics
   - Include story points, commits, and issue tracking per sprint
   - Extract and display issue codes from Jira data
   - Save to `ux/web/data/team_sprint_stats.json`

4. **Developer activity JSON (update/display)**
   - Generate developer-focused activity statistics
   - Track activity by sprint and last 3 days
   - Include Jira actions (issues created/updated/assigned) and repo actions (commits)
   - Provide all-time developer summaries with sprint breakdowns
   - Save to `ux/web/data/developer_activity.json`

5. **Generate self-sufficient HTML dashboard**
   - Automatically process all HTML files in `ux/web/` directory
   - Generate standalone HTML files in the `dist/` directory
   - Embed CSS styles and JSON data for offline viewing
   - Create timestamped backups of existing files
   - Support multiple dashboard types (sprint analytics, KPI, developer activity)
   - Smart detection of correct data source based on HTML filename

6. **Exit**

### Dashboard Features

#### Sprint Analytics Dashboard
- **Sprint-based Tracking**: Shows activity organized by sprint periods
- **Story Points Integration**: Dedicated tracking of story points per sprint
- **Interactive Table**: Sortable table with all developer metrics
- **Individual Cards**: Detailed cards for each developer with sprint breakdown
- **Issue Codes Display**: Visual badges showing relevant issue codes
- **Commit Activity**: Git commit tracking aligned with sprint periods

#### KPI Dashboard
- **Key Performance Indicators**: Comprehensive team and individual KPIs
- **Sprint Progress**: Visual representation of sprint completion rates
- **Developer Performance**: Individual developer statistics and trends
- **Issue Resolution**: Tracking of issue resolution rates and patterns
- **Modern UI**: Responsive design with gradient backgrounds and hover effects

#### Developer Activity Dashboard
- **Individual Developer Focus**: Detailed view of each developer's contributions
- **Sprint Filtering**: View activity for specific sprints or all-time summary
- **Last 3 Days Activity**: Real-time tracking of recent developer work
- **Visual Charts**: Pie charts for activity distribution and bar charts for Jira vs Repo actions
- **Comprehensive Metrics**: Track Jira actions (issues created/updated/assigned/status changes) and repo actions (commits)
- **Sprint Breakdown**: See each developer's activity across all sprints they participated in
- **Average Activity**: Calculate average activity per sprint for performance insights

### Generated Files

When using option 5, the tool generates:
- `dist/team-sprint-stats.html`: Self-sufficient sprint analytics dashboard
- `dist/team-sprint-kpi-dashboard.html`: Self-sufficient KPI dashboard
- `dist/developer-activity-dashboard.html`: Self-sufficient developer activity dashboard
- Timestamped backups of any existing files

These files can be:
- Opened directly in any web browser
- Shared without external dependencies
- Deployed to web servers for team access
- Used offline without internet connectivity
- Viewed on any device (desktop, tablet, mobile)

## Data Structure

### Story Points Tracking
The tool now tracks story points in multiple ways:
- **Time-based**: Story points closed in the last 1, 3, and 7 days
- **Total**: Cumulative story points assigned to each developer
- **Visual Display**: Color-coded metrics in both dashboards

### Developer Activity Tracking
The developer activity feature provides:
- **Sprint-based Activity**: Track Jira and repo actions per sprint
- **Recent Activity**: Last 3 days activity with detailed breakdowns
- **All-time Summaries**: Comprehensive developer profiles across all sprints
- **Activity Breakdown**: Separate tracking of:
  - Issues created, assigned, updated
  - Status changes
  - Commits
- **Performance Metrics**: Average activity per sprint for each developer

### Issue Code Extraction
- Automatically extracts issue codes (e.g., SET-12345) from Jira data
- Displays codes as styled badges in the dashboards
- Supports overflow display for developers with many issue codes

### Enhanced Statistics
- **Productivity Scores**: Calculated based on commits and issue activity
- **Commit-to-Issue Ratios**: Helps identify development patterns
- **Time-based Metrics**: Activity tracking over multiple time periods (last 3 days, per sprint, all-time)
- **Comprehensive Developer Profiles**: Complete view of each team member's contributions
- **Team Filtering**: Respects EXCLUDED_EMAILS environment variable to filter out non-team members

## File Structure

```
sdm-tools/
├── sdm_tools/           # Main package
├── ux/web/              # Dashboard templates and assets
│   ├── *.html          # Dashboard templates
│   ├── shared-dashboard-styles.css
│   └── data/           # JSON data files
├── dist/               # Generated self-sufficient dashboards
├── requirements.txt    # Python dependencies
├── .env               # Environment configuration
└── README.md          # This file
```

## Notes

- **Configuration**: All required environment variables must be set before running the tool
- **Data Persistence**: All data is stored in SQLite database for fast access and reliability
- **Automatic Backups**: Existing files are automatically backed up with timestamps
- **Responsive Design**: Dashboards work on desktop, tablet, and mobile devices
- **Offline Capability**: Generated HTML files work without internet connectivity
- **Extensible**: Easy to add new dashboard types by creating HTML templates in `ux/web/`

## Troubleshooting

### Common Issues
1. **Missing Environment Variables**: Ensure all required variables are set in your `.env` file
2. **Jira Connection Issues**: Verify your API token and URL are correct
3. **Repository Access**: Ensure the `REPO_PATH` points to a valid Git repository
4. **File Permissions**: Check that the tool has write access to create database and output files

### Dashboard Generation
- If dashboards don't generate, ensure JSON data files exist:
  - Run option 3 for sprint analytics dashboard
  - Run option 4 for developer activity dashboard
- Check that the `ux/web/` directory contains the HTML template files
- Verify the `dist/` directory is writable
- The tool automatically detects which JSON file to use based on the HTML filename:
  - Files with "activity" use `developer_activity.json`
  - Files with "sprint" use `team_sprint_stats.json`
  - Files with "kpi" use appropriate KPI data

Feedback is welcome juan.gramajo@telus.com
