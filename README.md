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
- **Team Statistics**: Generate comprehensive team statistics in JSON format
- **Time-based Metrics**: Track activity over 1, 3, and 7-day periods
- **Story Points Tracking**: Monitor story points closed by developers
- **Issue Code Extraction**: Automatically extract and display issue codes from Jira data
- **Productivity Scoring**: Calculate productivity scores based on commits and issues

### Interactive Dashboards
- **Self-Sufficient HTML Dashboards**: Generate standalone HTML files with embedded data and styles
- **Dual Dashboard Types**:
  - **Basic Stats Dashboard**: Time-based activity with story points tracking
  - **Simple Stats Dashboard**: Comprehensive developer statistics with issue codes
- **Responsive Design**: Modern, mobile-friendly interface using TailwindCSS
- **Real-time Data**: Embedded JSON data for instant loading without external dependencies

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
- `DB_NAME`: Name of the SQLite database file (default: `sdm_tools.db`)
- `TABLE_NAME`: Name of the table to store issues (default: `iotmi_3p_issues`)
- `BASIC_STATS`: Path to the basic statistics JSON file (default: `ux/web/data/team_basic_stats.json`)
- `SIMPLE_STATS`: Path to the simple statistics JSON file (default: `ux/web/data/team_simple_stats.json`)

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
export BASIC_STATS='ux/web/data/team_basic_stats.json'
export SIMPLE_STATS='ux/web/data/team_simple_stats.json'
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

3. **Team basic stats JSON (update/display)**
   - Generate time-based statistics (1, 3, 7 days)
   - Include story points closed by time period
   - Extract and display issue codes from Jira data
   - Save to `BASIC_STATS` file location

4. **Team simple stats JSON (update/display)**
   - Generate comprehensive developer statistics
   - Include productivity scores and commit-to-issue ratios
   - Calculate total story points and issue codes per developer
   - Save to `SIMPLE_STATS` file location

5. **Generate self-sufficient HTML dashboards**
   - **NEW FEATURE**: Automatically process all HTML files in `ux/web/` directory
   - Generate standalone HTML files in the `dist/` directory
   - Embed CSS styles and JSON data for offline viewing
   - Create timestamped backups of existing files
   - Support both basic and simple dashboard types

6. **Exit**

### Dashboard Features

#### Basic Stats Dashboard
- **Time-based Activity Tracking**: Shows commits, Jira updates, and story points for 1, 3, and 7-day periods
- **Interactive Table**: Sortable table with all developer metrics
- **Individual Cards**: Detailed cards for each developer with activity breakdown
- **Story Points Integration**: Dedicated columns and sections for story points closed
- **Issue Codes Display**: Purple badges showing relevant issue codes

#### Simple Stats Dashboard
- **Comprehensive Statistics**: Total commits, issues, story points, and productivity scores
- **Top Performers**: Ranked list of top-performing developers
- **Issue Code Badges**: Visual display of issue codes worked on
- **Productivity Metrics**: Commit-to-issue ratios and productivity scoring
- **Modern UI**: Responsive design with gradient backgrounds and hover effects

### Generated Files

When using option 5, the tool generates:
- `dist/team-basic-stats-dashboard.html`: Self-sufficient basic stats dashboard
- `dist/team-simple-stats-dashboard.html`: Self-sufficient simple stats dashboard
- Timestamped backups of any existing files

These files can be:
- Opened directly in any web browser
- Shared without external dependencies
- Deployed to web servers for team access
- Used offline without internet connectivity

## Data Structure

### Story Points Tracking
The tool now tracks story points in multiple ways:
- **Time-based**: Story points closed in the last 1, 3, and 7 days
- **Total**: Cumulative story points assigned to each developer
- **Visual Display**: Color-coded metrics in both dashboards

### Issue Code Extraction
- Automatically extracts issue codes (e.g., SET-12345) from Jira data
- Displays codes as styled badges in the dashboards
- Supports overflow display for developers with many issue codes

### Enhanced Statistics
- **Productivity Scores**: Calculated based on commits and issue activity
- **Commit-to-Issue Ratios**: Helps identify development patterns
- **Time-based Metrics**: Activity tracking over multiple time periods
- **Comprehensive Developer Profiles**: Complete view of each team member's contributions

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
- If dashboards don't generate, ensure JSON data files exist (run options 3 and 4 first)
- Check that the `ux/web/` directory contains the HTML template files
- Verify the `dist/` directory is writable

For additional support or feature requests, please refer to the project documentation or contact the development team.
