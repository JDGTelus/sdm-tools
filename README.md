# SDM-Tools

SDM-Tools is a command-line interface (CLI) tool designed for Software Developer Managers (SDMs) to manage and analyze their team's Jira tasks and repository commits. The tool provides customized insights and actions, making it easier to track and manage issues, backlog, sprint planning, and commit history.

## Features

- Identify active developers working on Jira stories or bugs.
- Manage backlog and sprint planning.
- Monitor current work and provide detailed views of tasks.
- Store and display Jira issues with customizable columns.
- Backup and update Jira data with ease.
- Fetch and store commit information from the repository.
- Display commit information with pagination and colorful output.
- Generate and display team statistics in JSON format.
- Backup existing statistics files automatically with timestamps.

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
- `BASIC_STATS`: Name of the team statistics JSON file (default: `team_simple_stats.json`)

#### Additional Variables
- `REPO_NAME`: Name of the repository for reference (e.g., `your-repo-name`)

Example of recommended `.env` file:

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
export BASIC_STATS='team_simple_stats.json'
```

## Usage

Load environment variables and run the CLI tool:

1. **Load environment variables**:
   ```bash
   set -a; source .env; set +a
   ```
2. **Run the CLI tool**:
   ```bash
   python -m sdm_tools.cli
   ```

Follow the on-screen menu to manage and display Jira issues and commit information.

### Notes
- **Configuration**: All environment variables are required and must be set before running the tool.
- **User-Friendly Output**: The script stores meaningful data, and the `DISPLAY_COLUMNS` environment variable is set to display relevant fields. Adjust the `DISPLAY_COLUMNS` as needed to improve the user experience.
- **Commit Information**: The script fetches commit information from the repository and stores it in the `git_commits` table in the SQLite database. You can update and display commit information using the CLI tool.
- **Team Statistics**: The tool can generate team statistics in JSON format, automatically backing up existing files with timestamps before creating new ones.
