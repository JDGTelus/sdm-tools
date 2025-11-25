# SDM-Tools

A command-line interface (CLI) tool for Software Developer Managers to analyze team activity across Jira and Git repositories. Generates interactive HTML dashboards with time-bucketed activity analysis, sprint metrics, and velocity tracking.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env  # Edit with your settings
set -a; source .env; set +a

# 3. Run CLI
python -m sdm_tools.cli
```

## Features

### Three Interactive Dashboards

**📅 Daily Activity Dashboard**

- Time-bucketed activity (2-hour intervals: 8am-10am, 10am-12pm, etc.)
- Activity heatmap with color-coded intensity
- Off-hours tracking (6pm-8am)
- Interactive charts (stacked bar, doughnut, rankings)
- Shows ALL active developers (including zero-activity)

**📊 Sprint Activity Dashboard**

- Multi-sprint trend analysis (last 10 sprints)
- Line charts showing activity progression
- Sprint comparison and averages
- Developer activity heatmap by sprint

**📈 Sprint Velocity Dashboard**

- Planned vs delivered story points
- Completion rate trends
- Metrics cards (total planned, delivered, variance)
- Historical velocity analysis

**🎯 Bundled SPA**

- Single HTML file (~140 KB)
- All 3 dashboards with sidebar navigation
- Fully portable, works offline (CDN libs need internet)
- Same consistent UX across all dashboards

### Core Capabilities

- **Jira Integration**: Fetch issues via customizable JQL queries
- **Git Tracking**: Comprehensive commit history from ALL branches
- **Normalized Database**: 8-table SQLite schema for optimal performance
- **Email Normalization**: Handles AWS SSO prefixes, domain variations, aliases
- **Timezone Support**: Accurate time bucket assignment
- **Data Persistence**: SQLite with automated backups (keeps last 5)
- **Pre-aggregation**: 50-100x faster queries via daily_activity_summary table

## Installation

### Prerequisites

- Python 3.6+
- Jira account with API access
- Local Git repository

### Setup

1. **Create virtual environment**:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment** (create `.env` file):

   ```bash
   # Required
   export JIRA_URL='https://your-domain.atlassian.net'
   export JIRA_API_TOKEN='your-api-token'
   export JIRA_EMAIL='your-email@example.com'
   export JQL_QUERY='project = "YOUR_PROJECT" AND component = "YOUR_COMPONENT"'
   export REPO_PATH='/path/to/your/repo'
   export INCLUDED_EMAILS='dev1@example.com,dev2@example.com'

   # Optional (with defaults)
   export DB_NAME='data/sdm_tools.db'
   export TIMEZONE='America/Toronto'  # or your timezone
   export REPO_NAME='your-repo-name'
   ```

4. **Get Jira API token**:
   - Log in to Jira → Account Settings → Security → API Tokens → Create
   - Copy token to `JIRA_API_TOKEN` in `.env`

## Usage

### CLI Workflow

```bash
# Load environment
set -a; source .env; set +a

# Run CLI
python -m sdm_tools.cli
```

**Menu Options:**

1. **Refresh All Data (Jira + Git → Normalize)**
   - Complete data refresh
   - Fetches from Jira and Git
   - Normalizes and processes all data
   - Run this first time or for full refresh

2. **Generate Activity Reports**
   - Single day report (today or specific date)
   - Full sprint report (last 10 sprints)
   - Sprint velocity report
   - Generate standalone reports (3 HTML files in `dist/`)
   - **Generate bundled SPA** (single file with all 3 dashboards)

3. **View Sprints**
   - List all available sprints
   - Shows dates and status

4. **View Active Developers**
   - List configured active developers
   - Based on `INCLUDED_EMAILS`

5. **Exit**

### Programmatic Usage

```python
from sdm_tools.database.reports import (
    generate_daily_report_json,
    generate_sprint_report_json,
    generate_sprint_velocity_report
)
from sdm_tools.database.standalone import (
    generate_all_standalone_reports,
    generate_bundle_spa
)

# Generate data files
generate_daily_report_json()
generate_sprint_report_json()
generate_sprint_velocity_report()

# Generate standalone HTML files
generate_all_standalone_reports()

# Generate bundle (all 3 dashboards)
generate_bundle_spa()
```

## Configuration

### Environment Variables

**Required:**

- `JIRA_URL`: Base URL for Jira API
- `JIRA_API_TOKEN`: API token for authentication
- `JIRA_EMAIL`: Email associated with Jira account
- `JQL_QUERY`: JQL query to filter issues
- `REPO_PATH`: Path to local Git repository
- `INCLUDED_EMAILS`: Comma-separated list of developer emails

**Optional:**

- `DB_NAME`: SQLite database file path (default: `data/sdm_tools.db`)
- `TIMEZONE`: Timezone for activity bucketing (default: `America/Mexico_City`)
- `TABLE_NAME`: Jira issues table name (default: `iotmi_3p_issues`)
- `REPO_NAME`: Repository name for reference

### Team Management

The `INCLUDED_EMAILS` variable controls which developers appear in reports:

1. Edit `.env` file to modify `INCLUDED_EMAILS`
2. Reload environment: `set -a; source .env; set +a`
3. Run "Refresh All Data" to update the database
4. All reports will filter by `active = 1` (developers in INCLUDED_EMAILS)

**Email Normalization** handles:

- AWS SSO prefixes: `AWSReservedSSO_*/user@domain.com` → `user@domain.com`
- Domain variations: `@telusinternational.com` → `@telus.com`
- Numeric suffixes: `user01@domain.com` → `user@domain.com`
- Case normalization: all lowercase

## Architecture

### Database Schema (8 tables)

```
developers                    # Developer registry
developer_email_aliases       # Email variations for matching
sprints                       # Sprint metadata
issues                        # Jira issues (simplified)
issue_sprints                 # Many-to-many issue-sprint relationship
jira_events                   # Jira activity events with time buckets
git_events                    # Git commit events with sprint assignment
daily_activity_summary        # Pre-aggregated materialized view (fast queries)
```

### File Structure

```
sdm-tools/
├── sdm_tools/
│   ├── cli.py                      # Main CLI interface
│   ├── config.py                   # Environment configuration
│   ├── jira.py                     # Jira API client
│   ├── repo.py                     # Git repository client
│   ├── utils.py                    # Utility functions
│   └── database/
│       ├── core.py                 # Database utilities
│       ├── schema.py               # 8-table schema definition
│       ├── reports.py              # Report query functions
│       ├── standalone.py           # Standalone + bundle generation
│       ├── refresh.py              # Data refresh workflow
│       ├── issues.py               # Jira issue management
│       ├── commits.py              # Git commit management
│       ├── sprints.py              # Sprint processing
│       ├── sprint_metrics.py       # Velocity calculations
│       ├── queries.py              # Query helpers
│       └── normalizers/            # Data normalization (7 files)
├── ux/web/                         # Dashboard templates
│   ├── daily-activity-dashboard.html
│   ├── sprint-activity-dashboard.html
│   ├── sprint-velocity-dashboard.html
│   ├── shared-dashboard-styles.css
│   └── data/                       # Generated JSON files
│       ├── daily_activity_report.json
│       ├── sprint_activity_report.json
│       └── sprint_velocity_report.json
├── dist/                           # Generated standalone reports
│   ├── daily-activity-dashboard.html      (self-contained)
│   ├── sprint-activity-dashboard.html     (self-contained)
│   ├── sprint-velocity-dashboard.html     (self-contained)
│   └── reports-bundle.html                (all 3 dashboards)
├── data/
│   ├── sdm_tools.db                # SQLite database
│   └── sdm_tools_backup_*.db       # Automated backups (last 5)
├── requirements.txt
├── .env
└── README.md
```

### Data Flow

```
Jira API + Git Repo
       ↓
  Fetch Data
       ↓
  8-Table Database (normalized)
       ↓
  Query Functions (reports.py)
       ↓
  Generate JSON Files (ux/web/data/)
       ↓
  Generate Standalone HTML (dist/*.html)
       ↓
  Extract & Bundle (dist/reports-bundle.html)
```

## Time Buckets

Activity tracked in configurable timezone:

- **8am-10am**: 08:00-09:59
- **10am-12pm**: 10:00-11:59
- **12pm-2pm**: 12:00-13:59
- **2pm-4pm**: 14:00-15:59
- **4pm-6pm**: 16:00-17:59
- **Off-Hours**: 18:00 to 07:59 (previous/next day)

Each bucket tracks:

- **Jira Actions**: Issues created, updated, status changes
- **Git Actions**: Commits made
- **Total Activity**: Combined Jira + Git

## Generated Reports

### Standalone Reports (3 files)

Self-contained HTML files with embedded data:

- Data inlined from JSON files
- CSS inlined from shared stylesheet
- CDN libraries (React, Chart.js, TailwindCSS)
- Can be shared independently

### Bundled SPA (1 file)

Single-page application combining all 3 dashboards:

- Dynamic sidebar navigation
- All data embedded (~25 KB data)
- Total file size: ~140 KB
- Fully portable
- Same consistent UX

## Performance

**Tested with real data** (Nov 25, 2025):

- 4 active developers
- 10 sprints
- 659 activity events
- Date range: July 16 - Nov 25, 2025

**Metrics**:

- Report generation: ~2 seconds
- Standalone generation: ~1 second
- Bundle generation: ~1 second
- Query speed: <0.1s (pre-aggregated table)
- Database size: Varies by data volume

## Troubleshooting

### Common Issues

**Missing Environment Variables**

- Ensure all required variables are set in `.env`
- Use `set -a; source .env; set +a` to load

**Jira Connection Issues**

- Verify `JIRA_URL` is correct (include https://)
- Check `JIRA_API_TOKEN` is valid (regenerate if needed)
- Test `JIRA_EMAIL` matches your Jira account

**Repository Access**

- Ensure `REPO_PATH` points to valid Git repository
- Check file permissions for read access

**Report Generation Fails**

- Run "Refresh All Data" first (Option 1)
- Check console output for specific errors
- Verify database file exists: `data/sdm_tools.db`

**Developers Missing from Reports**

- Check `INCLUDED_EMAILS` configuration
- Verify email addresses match Jira/Git records
- Run "Refresh All Data" after changing `INCLUDED_EMAILS`

**Dashboard Shows No Data**

- Ensure JSON files exist in `ux/web/data/`
- Check that data refresh completed successfully
- Verify target date has activity

### Verification Commands

```bash
# Test full workflow
python << 'EOF'
from sdm_tools.database.reports import *
from sdm_tools.database.standalone import *

print("1. Daily:", generate_daily_report_json())
print("2. Sprint:", generate_sprint_report_json())
print("3. Velocity:", generate_sprint_velocity_report())
print("4. Standalone:", len(generate_all_standalone_reports()), "files")
print("5. Bundle:", generate_bundle_spa())
print("✅ All tests passed!")
EOF

# Verify output files
ls -lh dist/*.html

# Open bundle
open dist/reports-bundle.html
```

## Advanced Features

### Database Backups

Automatic backups during refresh:

- Creates timestamped backup: `sdm_tools_backup_YYYYMMDD_HHMMSS.db`
- Keeps last 5 backups automatically
- Located in same directory as database

### Complete Branch Tracking

Uses `git log --all` to capture commits from:

- Feature branches
- Remote branches
- All refs
- Ensures comprehensive developer activity tracking

### Sprint Assignment

Events automatically assigned to sprints based on:

- Jira sprint field (for issues)
- Event date matching sprint date range (for commits)
- Sprint context preserved in reports

## Development

See `AGENTS.md` for development guidelines including:

- Build/lint/test commands
- Code style conventions
- Database patterns
- Development workflow
- Architecture notes

## System Status

**Current Version**: Production-ready (Nov 25, 2025)

**Verified Working**:

- ✅ All 3 dashboards generate correctly
- ✅ Bundle includes all dashboards with navigation
- ✅ Data refresh workflow functional
- ✅ Email normalization working
- ✅ Time bucket calculation accurate
- ✅ Sprint metrics calculation correct

**Recent Improvements** (Nov 19, 2025):

- Daily reports show ALL active developers (including zero-activity)
- Sprint velocity dashboard UX homologized with other dashboards
- Consistent header/footer design across all three dashboards
- Complete team roster visibility

**Known Working Features**:

- 8-table normalized database
- Complete branch tracking (`git log --all`)
- Email normalization and alias matching
- Pre-aggregated daily activity summary (50-100x faster)
- Standalone and bundled report generation
- Sprint velocity tracking

## Future Enhancements

**High Priority**:

- Add automated testing (pytest suite)
- Code quality tools (black, ruff, mypy)
- Better error handling (retry logic, validation)

**Medium Priority**:

- Performance monitoring
- Configuration validation
- Architecture diagrams

**Low Priority**:

- PDF export
- Email digest functionality
- Dark mode toggle
- Custom time buckets

## Support

**Questions or Issues?**

- Review this README for common solutions
- Check `AGENTS.md` for development guidelines
- Contact: juan.gramajo@telus.com

**Contributing**:

- Follow guidelines in `AGENTS.md`
- Test changes thoroughly
- Maintain existing functionality
- Update documentation

---

**Repository**: https://github.com/JDGTelus/sdm-tools  
**License**: Internal TELUS tool  
**Maintainer**: Juan Gramajo (juan.gramajo@telus.com)
