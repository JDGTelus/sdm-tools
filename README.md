# SDM-Tools

A Python CLI tool for Software Developer Managers that aggregates Jira and Git data into an 8-table normalized SQLite database, then generates interactive HTML dashboards showing time-bucketed developer activity, sprint metrics, and velocity tracking.

**Tech Stack**: Python 3.6+, SQLite, Rich (CLI), React/Chart.js/TailwindCSS (dashboards)

**Core Value Proposition**: Transform scattered Jira/Git data into actionable insights via pre-aggregated queries (50-100x faster than real-time analysis).

---

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

---

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

---

## **Architecture Overview**

### **Data Flow Pipeline**

```
┌─────────────────┐     ┌─────────────────┐
│   Jira API      │     │   Git Repo      │
│   (REST)        │     │   (git log)     │
└────────┬────────┘     └────────┬────────┘
         │                       │
         └──────────┬────────────┘
                    │
         ┌──────────▼──────────┐
         │  Temporary DB       │  ← Raw data storage
         │  (sdm_tools_temp.db)│
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  Normalizers (7)    │  ← Email matching, timezone
         │  Data transformation│     conversion, sprint assignment
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  Production DB      │  ← 8 normalized tables
         │  (sdm_tools.db)     │     + materialized view
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  Report Queries     │  ← Pre-aggregated joins
         │  (reports.py)       │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  JSON Files         │  ← Data for dashboards
         │  (ux/web/data/)     │
         └──────────┬──────────┘
                    │
         ┌──────────▼──────────┐
         │  HTML Generation    │  ← Standalone + Bundle
         │  (standalone.py)    │     SPAs with inlined data
         └─────────────────────┘
```

---

## **Database Schema (Critical)**

The 8-table normalized schema at `sdm_tools/database/schema.py:9-183`:

### **Core Tables**

1. **`developers`** - Central registry, `active` flag controls report visibility
2. **`developer_email_aliases`** - Email variations (AWS SSO, domains)
3. **`sprints`** - Jira sprint metadata with local date conversion
4. **`issues`** - Simplified Jira issues (story points, dates)
5. **`issue_sprints`** - Many-to-many issue↔sprint relationship

### **Event Tables**

6. **`jira_events`** - Activity events with time buckets (created, updated, status changes)
7. **`git_events`** - Commit events with time buckets and sprint assignment
8. **`daily_activity_summary`** - **Materialized view** (pre-aggregated by date/developer/time_bucket)

**Key Insight**: All queries hit `daily_activity_summary`, not raw event tables. This is the performance secret.

---

## **Critical Implementation Details**

### **1. Email Normalization** (`sdm_tools/database/normalizers/email_normalizer.py`)

Handles edge cases:

- AWS SSO: `AWSReservedSSO_*/user@domain.com` → `user@domain.com`
- Domain variations: `@telusinternational.com` → `@telus.com`
- Numeric suffixes: `user01@domain.com` → `user@domain.com`

**Why this matters**: Git and Jira use different email formats. Normalization ensures developer matching works.

### **2. Time Bucket Assignment** (`sdm_tools/utils.py`)

Events are bucketed into:

- **8am-10am**, **10am-12pm**, **12pm-2pm**, **2pm-4pm**, **4pm-6pm**
- **off_hours** (18:00-07:59)

All timestamps converted to configured timezone (default: `America/Mexico_City`) before bucketing.

**Why this matters**: Manager visibility into work patterns and off-hours activity.

### **3. Sprint Assignment Logic**

- **Jira events**: Use issue's sprint field
- **Git commits**: Match commit date to sprint date ranges
- Sprints stored with both UTC and local dates for accurate date-range queries

### **4. Active Developer Filtering**

The `INCLUDED_EMAILS` env var drives the `developers.active` flag. **Every query** filters by `active = 1`.

**Why this matters**: Team changes don't pollute reports—just update `.env` and refresh.

---

## **Key Workflows**

### **Full Refresh Workflow** (`sdm_tools/database/refresh.py:76-200`)

```python
refresh_database_workflow():
  1. Backup current DB (keeps last 5)
  2. Create temp DB (sdm_tools_temp.db)
  3. Fetch Jira issues → store in temp
  4. Extract sprints from issues → store in temp
  5. Fetch Git commits (git log --all) → store in temp
  6. Drop production tables
  7. Create fresh normalized schema
  8. Run 9-step normalization:
     - Extract/merge developers
     - Normalize sprints
     - Normalize issues
     - Link issues↔sprints
     - Extract Jira events with time buckets
     - Extract Git events with time buckets
     - Materialize daily_activity_summary
  9. Display stats, cleanup temp DB
```

**Duration**: ~2-5 minutes for typical dataset (659 events, 10 sprints, 4 devs)

### **Report Generation** (`sdm_tools/database/reports.py`)

Three report types:

1. **Daily Activity**: `generate_daily_report_json(target_date)` → `ux/web/data/daily_activity_report.json`
2. **Sprint Activity**: `generate_sprint_report_json()` → Last 10 sprints multi-sprint analysis
3. **Sprint Velocity**: `generate_sprint_velocity_report()` → Planned vs delivered story points

All use `query_daily_activity()` or `query_sprint_activity()` which hit `daily_activity_summary`.

### **Standalone HTML Generation** (`sdm_tools/database/standalone.py`)

```python
generate_standalone_report():
  1. Find HTML files in ux/web/
  2. Inline CSS from shared-dashboard-styles.css
  3. Detect JSON fetch() calls via regex
  4. Inline JSON data as embedded variables
  5. Write to dist/ (self-contained, ~140KB bundle)
```

**Bundle SPA** (`generate_bundle_spa()`): Extracts all 3 standalone reports, adds sidebar navigation, combines into single file.

---

## **Code Organization**

```
sdm_tools/
├── config.py                    # Env vars (JIRA_URL, INCLUDED_EMAILS, etc.)
├── cli.py                       # Menu system (5 options)
├── jira.py                      # Jira REST API client
├── repo.py                      # Git log wrapper (uses --all flag)
├── utils.py                     # Timezone, time buckets, console utils
└── database/
    ├── schema.py                # 8-table DDL + indexes
    ├── refresh.py               # Orchestrates full refresh
    ├── reports.py               # Query functions (570+ lines)
    ├── standalone.py            # HTML generation with inlining
    ├── issues.py                # Jira issue CRUD
    ├── commits.py               # Git commit CRUD
    ├── sprints.py               # Sprint processing
    ├── sprint_metrics.py        # Velocity calculations
    ├── queries.py               # Helper query functions
    └── normalizers/             # 7 normalizer modules
        ├── __init__.py          # Orchestrates normalize_all_data()
        ├── email_normalizer.py
        ├── developer_normalizer.py
        ├── sprint_normalizer.py
        ├── issue_normalizer.py
        ├── jira_event_normalizer.py
        └── git_event_normalizer.py
```

---

## **Common Gotchas** (From AGENTS.md)

1. **Import issues**: Use `from .. import config` (not `from ..config import DB_NAME`) when values change at runtime (refresh workflow modifies `config.DB_NAME`)

2. **Dashboard sync**: Changes to `ux/web/*.html` require regenerating `dist/` files (Option 2→4 or 2→5)

3. **Bundle generation fragility**: Uses regex to extract HTML sections—changes to template structure may break extraction

4. **Git branches**: Uses `git log --all` to capture ALL branches (feature, remote, etc.)

5. **No real-time data**: Dashboards are static JSON snapshots—refresh required for new data

---

## **Development Workflow**

### **Quick Start**

```bash
# 1. Setup
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your settings

# 2. Load env
set -a; source .env; set +a

# 3. First run
python -m sdm_tools.cli
# Choose: 1 (Refresh All Data) → 2 (Generate Reports) → 2 (Full sprint)

# 4. View
open dist/reports-bundle.html
```

### **Manual Testing** (No pytest suite yet)

```bash
# Full workflow test
1. Option 1: Refresh All Data
2. Option 2: Generate Activity Reports → All suboptions (1-5)
3. Verify HTML outputs in ux/web/ and dist/
4. Check browser console for JS errors
```

### **Syntax Check**

```bash
python -m py_compile sdm_tools/**/*.py
```

---

## **Code Style Conventions**

- **Naming**: `snake_case` (functions/vars), `UPPER_SNAKE_CASE` (constants), `PascalCase` (future classes)
- **Imports**: Stdlib → 3rd party → local; use `from .module import func` for specifics
- **Error handling**: Rich console for UX (`[bold red]`, `[yellow]`, `[green]`)
- **DB patterns**: Always `try/finally` with `conn.close()`; parameterized queries (`?` placeholders)
- **Indentation**: 4 spaces, ~80-120 chars/line (up to 150 acceptable)

---

## **Next Steps for Onboarding**

### **Day 1: Understand Data Flow**

1. Read `schema.py:9-183` - memorize the 8 tables
2. Trace `refresh.py:76-200` - full refresh workflow
3. Examine `normalizers/__init__.py:25-122` - 9-step normalization

### **Day 2: Query Layer**

1. Study `reports.py:15-150` - `query_daily_activity()`
2. Understand pre-aggregation in `git_event_normalizer.py` (materialize function)
3. Run CLI, generate reports, inspect JSON structure

### **Day 3: Dashboard Generation**

1. Review `standalone.py:12-100` - HTML inlining logic
2. Check `ux/web/*.html` - React components, Chart.js usage
3. Generate bundle, inspect file size/structure

### **Day 4: Make a Change**

1. Add a new time bucket (e.g., "6pm-8pm")
2. Update `utils.py`, normalizers, dashboards
3. Test full workflow

---

## **Open Issues / Tech Debt**

From `AGENTS.md:119-137`:

**High Priority**:

1. No test suite (pytest recommended)
2. No linting/formatting (black, ruff, mypy needed)
3. Missing error handling (retry logic for Jira API)

**Medium Priority**: 4. Large modules (`reports.py` > 500 lines) 5. No config validation (missing env vars fail silently)

**Low Priority**: 6. No CI/CD 7. Single Jira project support only 8. No PDF export

---

## **FAQ**

1. **Why temp DB during refresh?** (Answer: Isolation—if normalization fails, production DB unaffected)
2. **Why `active` flag vs deleting developers?** (Answer: Historical data preservation)
3. **Why local dates AND UTC dates in sprints?** (Answer: Timezone-aware date-range queries)
4. **Why bundle extracts from standalone, not vice versa?** (Answer: Standalone templates are source of truth, bundle is aggregator)

---
