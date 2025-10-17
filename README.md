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

#### Vite SPA (Recommended)
- **Modern React-based SPA**: Single-page application built with React, TypeScript, and Vite
- **Self-Contained Bundle**: All data and assets embedded at build time
- **Four Integrated Dashboards**:
  - **Team Sprint Dashboard**: Sprint-focused activity with developer performance cards
  - **Team KPI Dashboard**: Key performance indicators and team rankings
  - **Developer Activity Dashboard**: Individual activity tracking with sprint filtering and charts
  - **Developer Comparison Dashboard**: Compare individual performance against team benchmarks
- **Sidebar Navigation**: Seamless navigation between all dashboards
- **Interactive Visualizations**: Radar charts, pie charts, and bar charts using Chart.js
- **Responsive Design**: Mobile-friendly interface with Tailwind CSS
- **Offline Capable**: No external API calls, works completely offline
- **TypeScript Support**: Full type safety and modern development experience

#### Legacy HTML Dashboards (Deprecated)
- **Standalone HTML Files**: Individual HTML files with embedded data (will be removed in future version)
- **Limited Navigation**: Each dashboard is a separate file
- **Use Vite SPA Instead**: Recommended for better maintainability and user experience

## Setup

### Prerequisites

- Python 3.6 or higher
- Jira account with API access
- Local repository with commit history
- Node.js 20.19+ or 22.12+ (for Vite SPA generation)
- npm (comes with Node.js)

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
3. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Node.js dependencies** (for Vite SPA):
   ```bash
   cd reports-spa
   npm install
   cd ..
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

5. **Generate dashboards**
   - **Option B (Recommended): Vite SPA Single-File Bundle**
     - Builds modern React SPA into a single HTML file
     - Output: `dist/reports/index.html` (one file, ~597KB)
     - All JavaScript, CSS, and data inlined
     - Features sidebar navigation between all 4 dashboards
     - Modern UI with interactive charts and filtering
     - TypeScript-based for better code quality
     - Can be shared as a single file attachment
   - **Option A (Deprecated): Legacy HTML Files**
     - Generates individual standalone HTML files
     - Output: `dist/` directory with separate HTML files
     - No navigation between dashboards
     - Will be removed in a future version

6. **Exit**

### Dashboard Features (Vite SPA)

#### Team Sprint Dashboard (Landing Page)
- **Sprint Filtering**: Filter by sprint or view all sprints
- **Developer Performance Cards**: Visual cards showing key metrics per developer
- **Sprint Overview Cards**: Sprint-level statistics and summaries
- **Performance Table**: Comprehensive table with all developer metrics
- **Aggregated Metrics**: Team-wide statistics and averages

#### Team KPI Dashboard
- **Productivity KPIs**: Comprehensive productivity scoring
- **Completion Rate Tracking**: Story completion percentages
- **Story Points Analysis**: Sprint-based story points tracking
- **Developer Rankings**: Performance-based leaderboards
- **Trend Visualization**: Historical performance trends

#### Developer Activity Dashboard
- **Sprint Filtering**: View activity for specific sprints or all-time summary
- **Last 3 Days Activity**: Real-time tracking of recent developer work
- **Activity Distribution**: Pie chart showing top 10 developers by activity
- **Jira vs Repo Actions**: Bar chart comparing Jira and repository activity
- **Comprehensive Table**: Detailed activity breakdown with average per sprint
- **Activity Metrics**: Track issues created, updated, status changes, and commits

#### Developer Comparison Dashboard
- **Team Benchmarks**: View team average metrics across all sprints
- **Sprint-Specific Analysis**: Filter by individual sprint for detailed comparison
- **Developer Selection**: Choose any developer to compare against team average
- **Performance Indicators**: Visual indicators (▲▲, ▲, ●, ▼) showing performance vs team
- **Radar Chart**: Multi-dimensional performance profile comparison
- **Bar Chart**: Total contributions vs team benchmark
- **Performance Summary**: Automated strengths, key metrics, and improvement areas
- **Interactive Table**: Click any developer row to view detailed comparison
- **Completion Rate**: Individual vs team completion percentage

### Dashboard Navigation (Vite SPA)
- **Sidebar Menu**: Persistent sidebar with collapsible design
- **Active Route Highlighting**: Visual indication of current dashboard
- **Seamless Transitions**: Client-side routing for instant navigation
- **Mobile Responsive**: Sidebar collapses on mobile devices

### Generated Files

#### Vite SPA Bundle (Option 5b - Recommended)
When using option 5b, the tool generates:
- `dist/reports/index.html`: **Single self-contained HTML file (~597KB)**
  - All JavaScript inlined
  - All CSS inlined
  - All data embedded
  - No external dependencies

The SPA bundle:
- **Truly single-file**: Everything in one HTML file
- Contains all 4 dashboards in a single application
- Has all data embedded directly in the HTML
- Works completely offline without any external requests
- Can be shared as a single file or deployed to any web server
- Supports client-side routing for seamless navigation
- Can be opened directly in any browser
- Viewed on any device (desktop, tablet, mobile)

#### Legacy HTML Files (Option 5a - Deprecated)
When using option 5a, the tool generates:
- `dist/team-sprint-dashboard.html`: Sprint analytics dashboard
- `dist/team-sprint-kpi-dashboard.html`: KPI dashboard
- `dist/developer-activity-dashboard.html`: Activity dashboard
- `dist/developer-comparison-dashboard.html`: Comparison dashboard
- Timestamped backups of any existing files

**Note**: Legacy HTML generation is deprecated and will be removed in a future version.

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
├── sdm_tools/              # Main package
├── reports-spa/            # Vite SPA project (NEW)
│   ├── src/
│   │   ├── components/    # Reusable React components
│   │   ├── pages/         # Dashboard pages
│   │   ├── data/          # Data access layer
│   │   └── styles/        # CSS styles
│   ├── package.json       # Node.js dependencies
│   ├── vite.config.ts     # Vite configuration
│   └── tsconfig.json      # TypeScript configuration
├── ux/web/                 # Legacy dashboard templates (DEPRECATED)
│   ├── *.html             # Legacy dashboard templates
│   ├── shared-dashboard-styles.css
│   └── data/              # JSON data files
├── dist/
│   ├── reports/           # Vite SPA output (recommended)
│   └── *.html             # Legacy HTML files (deprecated)
├── requirements.txt        # Python dependencies
├── .env                   # Environment configuration
└── README.md             # This file
```

## Notes

- **Configuration**: All required environment variables must be set before running the tool
- **Data Persistence**: All data is stored in SQLite database for fast access and reliability
- **Vite SPA Recommended**: The new Vite SPA provides better maintainability and user experience
- **Legacy Deprecation**: Legacy HTML generation (option 5a) is deprecated and will be removed
- **Responsive Design**: Dashboards work on desktop, tablet, and mobile devices
- **Offline Capability**: Both Vite SPA and legacy HTML work without internet connectivity
- **Self-Contained Bundles**: All data is embedded at build time, no external API calls

## Troubleshooting

### Common Issues
1. **Missing Environment Variables**: Ensure all required variables are set in your `.env` file
2. **Jira Connection Issues**: Verify your API token and URL are correct
3. **Repository Access**: Ensure the `REPO_PATH` points to a valid Git repository
4. **File Permissions**: Check that the tool has write access to create database and output files

### Dashboard Generation

#### Vite SPA (Option 5b)
- If build fails, ensure JSON data files exist:
  - Run option 3 to generate sprint analytics (`ux/web/data/team_sprint_stats.json`)
  - Run option 4 to generate developer activity (`ux/web/data/developer_activity.json`)
- Verify Node.js and npm are installed (`node --version` should show 20.19+ or 22.12+)
- Check that `reports-spa/` directory exists with `package.json`
- Run `npm install` in the `reports-spa/` directory if dependencies are missing
- Build output will be in `dist/reports/` directory

#### Legacy HTML (Option 5a - Deprecated)
- Ensure JSON data files exist (run options 3 and 4)
- Check that the `ux/web/` directory contains the HTML template files
- Verify the `dist/` directory is writable
- The tool automatically detects which JSON file to use based on the HTML filename

Feedback is welcome juan.gramajo@telus.com
