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

1. **Refresh All Data (Jira + Git → Normalize)**
   - Complete data refresh workflow
   - Fetches from Jira and Git repositories
   - Normalizes and processes all data

2. **Generate Activity Reports**
   - **Single day report**: Time-bucketed activity for a specific date
   - **Full sprint report**: Multi-sprint activity trends and analysis
   - **Standalone reports**: Self-contained HTML files in `dist/`
   - **Bundled SPA**: Single-file app combining all reports with navigation

3. **View Sprints**
   - List all available sprints with metadata
   - View sprint dates and status

4. **View Active Developers**
   - List configured active developers
   - Based on `INCLUDED_EMAILS` configuration

5. **Exit**

### Managing Team Membership

**INCLUDED_EMAILS Configuration:**

The `INCLUDED_EMAILS` environment variable controls which developers appear in reports:

1. **Update Team Members**:
   - Edit `.env` file to modify `INCLUDED_EMAILS`
   - Reload environment: `set -a; source .env; set +a`
   - Run "Refresh All Data" (Option 1) to update the database

2. **How It Works**:
   - During refresh, developers matching `INCLUDED_EMAILS` are marked as `active = 1`
   - All reports filter by `active = 1` automatically
   - Zero-activity developers are shown in reports (since Nov 19, 2025)

3. **Email Normalization**:
   - System handles AWS SSO prefixes, domain variations, numeric suffixes
   - All emails normalized to lowercase
   - Automatic matching between Jira and Git identities

### Activity Dashboards

SDM Tools generates multiple types of interactive HTML dashboards with **consistent UX design**:

#### Daily Activity Dashboard
Provides comprehensive time-based analysis for a single day:
- **Time Buckets**: Activity in 2-hour intervals (8am-10am, 10am-12pm, etc.)
- **Activity Heatmap**: Color-coded table showing developer intensity
- **Interactive Charts**: Bar charts, doughnut charts, developer rankings
- **Off-Hours Tracking**: Work done outside standard hours
- **Complete Team Roster**: Shows ALL active developers, including those with zero activity

#### Sprint Activity Dashboard
Multi-sprint trend analysis and visualization:
- **Trend Charts**: Line charts showing activity progression across sprints
- **Sprint Comparison**: Compare activity across multiple sprints
- **Heatmap Table**: Developer activity by sprint
- **Statistical Averages**: Sprint and overall averages

#### Sprint Velocity Dashboard
Planned vs delivered story points analysis:
- **Velocity Trends**: Line charts showing sprint completion rates
- **Comparison Table**: Planned vs delivered points per sprint
- **Metrics Cards**: Total planned, delivered, completion rate, variance
- **Historical Analysis**: Track velocity trends across multiple sprints

#### Bundled SPA Report
Single-file application combining all reports:
- **Dynamic Discovery**: Automatically includes all reports from `dist/`
- **Side Navigation**: Toggle between different report views
- **Default Landing**: First report (alphabetically) shown by default
- **Fully Portable**: Single HTML file with all data embedded

#### Viewing Reports

**Standalone Reports** (in `ux/web/`):
- Open `ux/web/daily-activity-dashboard.html` for daily view
- Open `ux/web/sprint-activity-dashboard.html` for sprint view
- Requires data files in `ux/web/data/`

**Bundled Reports** (in `dist/`):
1. Generate standalone reports (CLI Option 2 → 4)
2. Generate bundle (CLI Option 2 → 5)
3. Open `dist/reports-bundle.html` in browser
4. Use sidebar to navigate between reports

All dashboards feature:
- **Consistent UX Design**: Homogenized headers and footers across all dashboards
- Self-contained with embedded React, Chart.js, and TailwindCSS
- Responsive design for desktop, tablet, and mobile
- Works offline (CDN libraries require internet)
- All data embedded at generation time
- Full-width gradient headers with container-based layouts
- GitHub link footer with SDM Tools attribution

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
- **Data Files** (`ux/web/data/`):
  - `daily_activity_report.json`: Daily activity data
  - `sprint_activity_report.json`: Multi-sprint data
  - `sprint_velocity_report.json`: Velocity metrics data
  
- **Standalone Reports** (`dist/`):
  - `daily-activity-dashboard.html`: Self-contained daily report
  - `sprint-activity-dashboard.html`: Self-contained sprint report
  - `sprint-velocity-dashboard.html`: Self-contained velocity report
  - `reports-bundle.html`: Bundled SPA with all reports
  
- **Database**:
  - `data/sdm_tools.db`: SQLite database with normalized data
  - Automated backups: `data/sdm_tools_backup_*.db` (keeps last 5)

## File Structure

```
sdm-tools/
├── sdm_tools/              # Main Python package
│   ├── database/           # Database modules
│   │   ├── core.py        # Core database utilities
│   │   ├── issues.py      # Jira issues management
│   │   ├── commits.py     # Git commits management
│   │   ├── sprints.py     # Sprint data processing
│   │   ├── normalize.py   # Data normalization
│   │   ├── reports.py     # Report generation
│   │   ├── standalone.py  # Standalone HTML generation
│   │   └── refresh.py     # Data refresh workflow
│   ├── cli.py             # CLI interface
│   ├── config.py          # Configuration management
│   ├── jira.py            # Jira API integration
│   ├── repo.py            # Git repository integration
│   └── utils.py           # Utility functions
├── ux/web/                 # Web dashboards (templates)
│   ├── daily-activity-dashboard.html
│   ├── sprint-activity-dashboard.html
│   ├── shared-dashboard-styles.css
│   └── data/              # Generated JSON files
│       ├── daily_activity_report.json
│       └── sprint_activity_report.json
├── dist/                   # Standalone reports (generated)
│   ├── daily-activity-dashboard.html
│   ├── sprint-activity-dashboard.html
│   └── reports-bundle.html
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
- **Note**: Zero-activity developers WILL appear in reports (as of Nov 19, 2025)
- To update team members: modify `.env` and run "Refresh All Data"

## Codebase Health & Next Steps

### Current Status (November 19, 2025)

✅ **Recent Improvements**:
- Daily reports now show ALL active developers (including zero-activity)
- Sprint velocity dashboard UX homologized with other dashboards
- Backend properly queries all active developers before overlaying activity
- Frontend filters removed to display complete team roster
- Consistent header/footer design across all three dashboards

✅ **Working Features**:
- Normalized database with 8 tables for optimal performance
- Complete branch tracking with `git log --all`
- Email normalization and alias matching
- Pre-aggregated daily activity summary (50-100x faster queries)
- Standalone and bundled report generation
- Sprint velocity tracking with planned vs delivered metrics

### Recommended Next Steps

#### High Priority

1. **Add Automated Testing**
   - Create pytest suite for database modules
   - Test email normalization edge cases
   - Test report generation with various data scenarios
   - Add integration tests for Jira/Git fetching

2. **Code Quality Tools**
   - Configure `black` for consistent formatting
   - Add `ruff` for fast linting
   - Set up pre-commit hooks for automatic formatting
   - Add type hints and run `mypy` for type checking

3. **Error Handling Improvements**
   - Add retry logic for Jira API calls
   - Better handling of missing/invalid environment variables
   - Graceful degradation when Git repo is unavailable
   - Validate JQL queries before executing

#### Medium Priority

4. **Performance Monitoring**
   - Add timing metrics to database queries
   - Log performance statistics during refresh
   - Monitor memory usage during large data imports
   - Optimize chart rendering for large datasets

5. **Configuration Management**
   - Validate `.env` file on startup
   - Provide helpful error messages for missing vars
   - Add configuration templates for common setups
   - Support multiple team configurations

6. **Documentation**
   - Add inline code comments for complex algorithms
   - Create architecture diagram showing data flow
   - Document database schema with entity-relationship diagram
   - Add troubleshooting guide for common issues

#### Low Priority

7. **Feature Enhancements**
   - Export reports to PDF format
   - Add email digest functionality
   - Support multiple Jira projects
   - Add custom time bucket configurations
   - Historical trend analysis across quarters

8. **UI/UX Improvements**
   - Add dark mode toggle
   - Improve mobile responsiveness
   - Add data export (CSV/JSON) from dashboards
   - Interactive date range selectors

### Code Smell Watch List

- **Database module coupling**: Consider breaking down large modules (reports.py is 500+ lines)
- **Configuration scattered**: Consolidate all config validation in one place
- **Error messages**: Standardize error message format across modules
- **Magic numbers**: Extract time bucket definitions to constants
- **Duplicate code**: Some chart generation logic is repeated across dashboards

### Technical Debt

- No automated tests (manual testing only)
- No linting or formatting enforcement
- No CI/CD pipeline
- Limited input validation
- Hard-coded chart colors and styles
- Bundle generation relies on regex parsing (fragile)

---

**Feedback & Contributions**: juan.gramajo@telus.com  
**Repository**: https://github.com/JDGTelus/sdm-tools
