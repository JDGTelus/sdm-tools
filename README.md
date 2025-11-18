# SDM-Tools

SDM-Tools is a command-line interface (CLI) tool designed for Software Developer Managers (SDMs) to analyze daily developer activity across Jira and repository commits. The tool generates a standalone HTML report showing time-bucketed activity analysis for your team.

## Features

### Core Functionality
- **Jira Integration**: Fetch and store Jira issues with customizable JQL queries
- **Commit Tracking**: Fetch and store commit information from ALL branches in local git repositories
- **Comprehensive Coverage**: Captures commits from feature branches, remote branches, and all refs
- **Normalized Database**: Efficient schema with email auto-mapping and sprint-based filtering
- **Data Persistence**: SQLite database for fast access and reliability
- **Pagination**: Display large datasets with colorful, paginated output

### Daily Activity Report
- **Time-Bucketed Analysis**: Activity broken down by 2-hour intervals throughout the workday
  - 8am-10am, 10am-12pm, 12pm-2pm, 2pm-4pm, 4pm-6pm
- **Off-Hours Tracking**: Identify and quantify work done outside standard hours (6pm-8am)
- **Activity Heatmap**: Color-coded visualization showing activity intensity per developer and time bucket
- **Interactive Charts**:
  - Activity by Time Bucket (stacked bar chart)
  - Regular vs Off-Hours Activity (doughnut chart)
  - Developer Rankings (vertical bar chart)
- **Standalone HTML Dashboard**: Self-contained report with embedded React, Chart.js, and all data
- **Timezone Support**: Respects configured timezone for accurate time bucket assignment

## Setup

### Prerequisites

- Python 3.6 or higher
- Jira account with API access
- Local git repository with commit history

### Jira API Token

To generate a Jira API token:
1. Log in to your Jira account
2. Navigate to your account settings
3. Find the "API tokens" section
4. Generate a new API token and copy it
5. Set the `JIRA_API_TOKEN` environment variable with the copied token

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

3. **Install Python dependencies**:
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
- `INCLUDED_EMAILS`: Comma-separated list of email addresses to include in reports (default: all)
- `TIMEZONE`: Timezone for activity bucketing (default: system timezone)

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
export DB_NAME='data/sdm_tools.db'
export TABLE_NAME='iotmi_3p_issues'
export REPO_PATH='/path/to/repo'
export REPO_NAME='your-repo-name'
export INCLUDED_EMAILS='alice@example.com,bob@example.com'
export TIMEZONE='America/Toronto'
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
   - Fetch commit information from ALL branches in the local repository
   - Captures commits from feature branches, remote branches, and all refs
   - Update commit data since the earliest Jira ticket date
   - Display commits with author information and pagination

3. **Daily activity report JSON (generate/display)**
   - Generate time-bucketed activity analysis for a specific date
   - Track activity by 2-hour time buckets (8am-10am, 10am-12pm, etc.)
   - Identify off-hours activity (outside standard work hours)
   - Include both Jira and repository actions per time bucket
   - Activity heatmap showing intensity by developer and time
   - Save to `ux/web/data/daily_activity_report.json`
   - Display formatted summary in the terminal

4. **Exit**

### Daily Activity Dashboard

The daily activity dashboard is a standalone HTML file that provides comprehensive time-based analysis:

#### Features
- **Date Selection**: Generate reports for any specific date (defaults to today)
- **Time Buckets**: Activity shown in 2-hour intervals:
  - 10am (8:00-9:59)
  - 12pm (10:00-11:59)
  - 2pm (12:00-13:59)
  - 4pm (14:00-15:59)
  - 6pm (16:00-17:59)
  - Off-Hours (6pm previous day - 8am current day)
- **Activity Heatmap**: Color-coded table showing developer activity intensity
- **Interactive Charts**:
  - Activity by Time Bucket (stacked bar chart)
  - Regular vs Off-Hours (doughnut chart)
  - Developer Rankings (bar chart)
- **Summary Cards**: Total developers, total activity, most active bucket, off-hours percentage

#### Viewing the Report

After generating the daily activity report JSON (option 3), the standalone HTML file can be found at:
```
ux/web/daily-activity-dashboard.html
```

To view it:
1. Open `ux/web/daily-activity-dashboard.html` in any web browser
2. The dashboard loads data from `ux/web/data/daily_activity_report.json`
3. No server needed - works completely offline

The dashboard features:
- Self-contained with embedded React, Chart.js, and TailwindCSS
- Responsive design for desktop, tablet, and mobile
- Color-coded activity levels (green for high, yellow for medium, etc.)
- Detailed breakdown of Jira vs Repository actions

## Data Structure

### Time Buckets

The tool tracks activity in the following time buckets (based on configured timezone):
- **8am-10am**: 08:00-09:59
- **10am-12pm**: 10:00-11:59
- **12pm-2pm**: 12:00-13:59
- **2pm-4pm**: 14:00-15:59
- **4pm-6pm**: 16:00-17:59
- **Off-Hours**: 18:00 previous day to 07:59 current day

### Activity Tracking

For each developer and time bucket, the tool tracks:
- **Jira Actions**: Issues created, updated, status changes
- **Repo Actions**: Commits made
- **Total Activity**: Combined Jira and repo actions

### Generated Files

The tool generates:
- `ux/web/data/daily_activity_report.json`: Daily activity data in JSON format
- Timestamped backups of previous reports

## File Structure

```
sdm-tools/
├── sdm_tools/              # Main Python package
│   ├── database/           # Database modules
│   │   ├── core.py        # Core database utilities
│   │   ├── issues.py      # Jira issues management
│   │   ├── commits.py     # Git commits management
│   │   ├── sprints.py     # Sprint data processing
│   │   └── stats.py       # Daily activity report generation
│   ├── cli.py             # CLI interface
│   ├── config.py          # Configuration management
│   ├── jira.py            # Jira API integration
│   ├── repo.py            # Git repository integration
│   └── utils.py           # Utility functions
├── ux/web/                 # Web dashboard
│   ├── daily-activity-dashboard.html  # Standalone dashboard
│   ├── shared-dashboard-styles.css    # Dashboard styles
│   └── data/              # Generated JSON files
│       └── daily_activity_report.json
├── data/                   # SQLite database
│   └── sdm_tools.db
├── requirements.txt        # Python dependencies
├── .env                   # Environment configuration
└── README.md             # This file
```

## Notes

- **Configuration**: All required environment variables must be set before running the tool
- **Data Persistence**: All data is stored in SQLite database for fast access and reliability
- **Timezone Awareness**: Activity buckets respect configured timezone for accurate tracking
- **Offline Capable**: The HTML dashboard works without internet connectivity
- **Self-Contained Report**: All data is embedded at generation time, no external API calls
- **Complete Commit Tracking**: Uses `git log --all` to capture commits from all branches, including feature branches that may not be merged yet. This ensures comprehensive developer activity tracking.

## Troubleshooting

### Common Issues

1. **Missing Environment Variables**: Ensure all required variables are set in your `.env` file
2. **Jira Connection Issues**: Verify your API token and URL are correct
3. **Repository Access**: Ensure the `REPO_PATH` points to a valid Git repository
4. **File Permissions**: Check that the tool has write access to create database and output files

### Daily Activity Report

- If report generation fails, ensure both Jira issues and git commits have been fetched first (options 1 and 2)
- The dashboard will show "no data" if `daily_activity_report.json` is missing - generate it using option 3
- For future dates, the tool will reject the request - only historical and current day reports are allowed
- Verify `TIMEZONE` environment variable matches your team's working timezone

### Data Issues

- If developers are missing from the report, check the `INCLUDED_EMAILS` configuration
- Ensure email addresses in Jira match those in git commit history
- Check that the target date has actual activity (commits and/or Jira updates)

---

**Feedback**: juan.gramajo@telus.com
