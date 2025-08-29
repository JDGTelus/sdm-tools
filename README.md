# SDM-Tools

SDM-Tools is a command-line interface (CLI) tool designed for Software Delivery Managers (SDMs) to manage and analyze their team's Jira tasks. The tool provides customized insights and actions, making it easier to track and manage issues, backlog, and sprint planning.

## Features

- Identify active developers working on Jira stories or bugs.
- Manage backlog and sprint planning.
- Monitor current work and provide detailed views of tasks.
- Store and display Jira issues with customizable columns.
- Backup and update Jira data with ease.

## Setup

### Prerequisites

- Python 3.6 or higher
- Jira account with API access

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

- `JIRA_URL`: Base URL for Jira API (e.g., `https://your-jira-domain.atlassian.net`)
- `JIRA_API_TOKEN`: API token for authentication
- `JIRA_EMAIL`: Email associated with the Jira account
- `COMPONENT_NAME`: Name of the component to filter issues by (optional, not used in the current script)
- `ISSUE_TYPES`: Comma-separated list of issue types to consider (e.g., `Epic,Story,Bug`)
- `DISPLAY_COLUMNS`: Comma-separated list of columns to display (e.g., `key,summary,status`)

Example of recommended `.env` to load:

```bash
#!/bin/bash
export JIRA_URL='https://your-jira-domain.atlassian.net'
export JIRA_API_TOKEN='your-api-token'
export JIRA_EMAIL='your-email@example.com'
export ISSUE_TYPES='Epic,Story,Bug'
export DISPLAY_COLUMNS='key,summary,status'
```

## Usage

Load env vars, and run the CLI tool:

```bash
set -a; source .env; set +a
python sdm_tools.py
```

Follow the on-screen menu to manage and display Jira issues.
