# SDM-Tools Database Normalization - Session State

**Date**: November 18, 2025  
**Current Phase**: Phase 1 Complete, Ready for Phase 2  
**Token Count**: ~110,000 / 200,000

---

## Project Overview

**Goal**: Transform SDM-Tools from a multi-dashboard analytics suite into a focused daily activity reporting tool with normalized database for sprint-based and date-range analysis.

### Key Requirements
- Fresh normalized database (drop/recreate approach)
- Auto-mapping email patterns (AWS SSO, domain variations)
- Sprint-based activity filtering
- Date range support (single day or multi-day)
- Pre-aggregated data (no complex client logic)
- Self-contained JSON reports (no fetch calls from SPA)

---

## Completed Work

### Phase 0: Initial Cleanup ✅
**Files Removed**:
- `ux/web/developer-activity-dashboard.html`
- `ux/web/developer-comparison-dashboard.html`
- `ux/web/team-sprint-dashboard.html`
- `ux/web/team-sprint-kpi-dashboard.html`
- `reports-spa/` (entire Vite directory)

**Code Simplified**:
- `stats.py`: 2,574 → ~700 lines (73% reduction)
- `cli.py`: 839 → ~310 lines (63% reduction)
- Menu options: 7 → 4 options
- Removed sprint analytics, developer activity, Vite generation

**Remaining Files**:
- `ux/web/daily-activity-dashboard.html` (standalone report)
- `ux/web/shared-dashboard-styles.css`

### Phase 1: Schema + Normalization ✅

#### Files Created
1. **`sdm_tools/database/schema.py`** (294 lines)
   - 8 normalized tables with proper indexes
   - Helper functions: `create_normalized_schema()`, `drop_all_tables()`, `get_table_stats()`

2. **`sdm_tools/database/normalize.py`** (~650 lines)
   - Email normalization with auto-mapping patterns
   - Developer extraction from Jira and Git
   - Sprint normalization with date parsing
   - Issue normalization (core fields only)
   - Jira event extraction (created, updated, status_changed)
   - Git event extraction with sprint assignment
   - Daily activity summary materialization
   - Main orchestration: `normalize_all_data()`

3. **`test_normalization.py`** (Test validation script)
   - Comprehensive validation tests
   - Email matching verification
   - Activity distribution analysis

4. **`PHASE1_VALIDATION.md`** (Detailed test results)

#### Database Schema (8 Tables)

```
1. developers
   - id, email, name, jira_account_id, active

2. developer_email_aliases  
   - developer_id, alias_email, source

3. sprints
   - id, name, state, start_date, end_date, start_date_local, end_date_local

4. issues
   - id, summary, status_name, assignee_id, creator_id, created_at, updated_at

5. issue_sprints (many-to-many)
   - issue_id, sprint_id

6. jira_events
   - id, developer_id, event_type, event_timestamp, event_date, 
     event_hour, time_bucket, issue_id, sprint_id

7. git_events
   - id, developer_id, commit_hash, commit_timestamp, commit_date,
     commit_hour, time_bucket, sprint_id, message

8. daily_activity_summary (materialized view)
   - id, activity_date, developer_id, sprint_id, time_bucket,
     jira_count, git_count, total_count
```

#### Test Results ✅

**Data Processed**:
- 152 developers (7 active from INCLUDED_EMAILS)
- 9 sprints (Sprint 64-72)
- 218 issues
- 636 Jira events
- 10,919 Git commits
- 6,512 daily summary rows

**Email Matching (100% Success)**:
All 7 INCLUDED_EMAILS developers matched with activity:

| Developer | Email | Git Commits | Jira Actions |
|-----------|-------|-------------|--------------|
| Carlos Carias | carlos.carias@telus.com | 102 | 51 |
| Christopher Soto | christopher.soto@telus.com | 39 | 58 |
| Daniel Quan | daniel.quan@telus.com | 16 | 32 |
| Diego Palacios | diego.palacios@telus.com | 93 | 40 |
| Edgar Calderon | edgar.calderon@telus.com | 127 | 28 |
| Henry Molina | henry.molina@telus.com | 108 | 137 |
| Oliver Sierra | oliver.sierra@telus.com | 153 | 45 |

**Email Normalization Patterns Working**:
- ✅ AWS SSO prefix removal: `AWSReservedSSO_xxx/user@domain` → `user@domain`
- ✅ Domain normalization: `@telusinternational.com` → `@telus.com`
- ✅ Numeric suffix removal: `user01@domain` → `user@domain`
- ✅ Case normalization: `User@Domain` → `user@domain`

**Sprint Assignment**:
- Sprint 72 (active): 190 total actions (89 Jira, 101 Git)
- Sprint 71 (closed): 157 total actions (49 Jira, 108 Git)
- Sprint 70 (closed): 87 total actions (36 Jira, 51 Git)

**Time Bucket Distribution**:
```
8am-10am:   1,473 actions
10am-12pm:  2,233 actions ← Peak
12pm-2pm:   1,750 actions
2pm-4pm:    2,170 actions
4pm-6pm:    2,198 actions
off_hours:  1,731 actions (15%)
```

---

## Current State

### Working Files
- Original database: `data/sdm_tools.db` (preserved)
- Test database: `data/sdm_tools_normalized_test.db` (validated)
- All Phase 1 implementation files in place

### Configuration (.env)
```bash
JIRA_URL='https://telusvideoservices.atlassian.net'
JIRA_API_TOKEN='[REDACTED]'
JIRA_EMAIL='[REDACTED]'
JQL_QUERY='project = "SET" AND component = "IOTMI 3P Connector" AND type = "Story"'
DISPLAY_COLUMNS='id,summary,description,assignee,reporter,status'
DB_NAME='data/sdm_tools.db'
TABLE_NAME='iotmi_3p_issues'
REPO_PATH='/Users/juangramajo/git/telus/telus-iot-sh-platform'
INCLUDED_EMAILS='carlos.carias@telus.com,christopher.soto@telus.com,daniel.quan@telus.com,diego.palacios@telus.com,edgar.calderon@telus.com,henry.molina@telus.com,oliver.sierra@telus.com'
TIMEZONE='America/Mexico_City'
```

---

## Phase 2: Next Steps

### Implementation Plan

#### 2.1 Database Refresh Workflow
**File**: `sdm_tools/database/core.py` or new `sdm_tools/database/refresh.py`

**Functions to create**:
```python
def backup_database(db_path):
    """Create timestamped backup before refresh."""
    # Copy to data/sdm_tools_backup_YYYYMMDD_HHMMSS.db
    # Keep last 5 backups only

def refresh_database_workflow():
    """Complete refresh workflow."""
    # 1. Backup current database
    # 2. Fetch fresh data from Jira (existing logic)
    # 3. Fetch fresh data from Git (existing logic)
    # 4. Drop all tables
    # 5. Create normalized schema
    # 6. Run normalization
    # 7. Display stats
```

#### 2.2 Update CLI Menu
**File**: `sdm_tools/cli.py`

**New menu structure**:
```
1. Refresh All Data (Jira + Git → Normalize → Materialize)
2. Generate Daily Activity Report
   ├─ a. Single day (with sprint context)
   ├─ b. Full sprint (all days)
   └─ c. Date range (custom range)
3. View Sprints
4. View Developers
5. Exit
```

**Functions to update/create**:
```python
def handle_refresh_all_data():
    """Orchestrate full data refresh."""
    # Call Jira fetch
    # Call Git fetch  
    # Run normalization
    # Show completion stats

def handle_daily_report_option():
    """Menu for report generation."""
    # Submenu for single day, sprint, or date range
    
def generate_single_day_report(target_date):
    """Generate report for one day."""
    # Query daily_activity_summary
    # Include sprint context
    # Generate JSON
    
def generate_sprint_report(sprint_id):
    """Generate report for entire sprint."""
    # Query all days in sprint
    # Aggregate by developer
    # Generate JSON

def generate_date_range_report(start_date, end_date):
    """Generate report for date range."""
    # Query date range
    # Group by date and developer
    # Generate JSON
```

#### 2.3 Update Stats Module
**File**: `sdm_tools/database/stats.py`

**Replace on-the-fly calculation with queries**:
```python
def query_daily_activity(target_date):
    """Query pre-aggregated daily activity."""
    # SELECT from daily_activity_summary
    # WHERE activity_date = target_date
    # Return structured data
    
def query_sprint_activity(sprint_id):
    """Query all activity for a sprint."""
    # SELECT from daily_activity_summary
    # WHERE sprint_id = sprint_id
    # GROUP BY activity_date
    # Return structured data

def query_date_range_activity(start_date, end_date):
    """Query activity for date range."""
    # SELECT from daily_activity_summary
    # WHERE activity_date BETWEEN start_date AND end_date
    # Return structured data
```

#### 2.4 JSON Output Formats

**Single Day Report** (`ux/web/data/daily_activity_report.json`):
```json
{
  "report_type": "daily",
  "metadata": {
    "report_date": "2025-11-18",
    "sprint": {"id": 163231, "name": "Sprint 72", "state": "active"}
  },
  "developers": [...],
  "summary": {...}
}
```

**Sprint Report** (`ux/web/data/sprint_activity_report.json`):
```json
{
  "report_type": "sprint",
  "metadata": {
    "sprint": {"id": 163231, "name": "Sprint 72", "dates": "..."}
  },
  "daily_breakdown": [...],
  "developer_summary": [...],
  "summary": {...}
}
```

**Date Range Report** (`ux/web/data/date_range_report.json`):
```json
{
  "report_type": "date_range",
  "metadata": {
    "start_date": "2025-11-10",
    "end_date": "2025-11-15",
    "sprints_included": [...]
  },
  "daily_breakdown": [...],
  "summary": {...}
}
```

#### 2.5 Update Database __init__.py
**File**: `sdm_tools/database/__init__.py`

**Add new exports**:
```python
from .schema import create_normalized_schema, drop_all_tables, get_table_stats
from .normalize import normalize_all_data
from .refresh import refresh_database_workflow, backup_database
```

---

## Quick Start for New Session

### 1. Verify Phase 1 Work
```bash
cd /Users/juangramajo/git/telus/playground/sdm-tools

# Test normalization still works
python test_normalization.py

# Check test database
sqlite3 data/sdm_tools_normalized_test.db ".tables"
```

### 2. Review Files Created in Phase 1
```bash
# Schema definitions
cat sdm_tools/database/schema.py

# Normalization logic
cat sdm_tools/database/normalize.py

# Validation results
cat PHASE1_VALIDATION.md
```

### 3. Start Phase 2 Implementation
Choose one of these approaches:

**Option A: Incremental (Recommended)**
1. Create `refresh_database_workflow()` function
2. Add to CLI menu as option 1
3. Test with current data
4. Then proceed to report generation updates

**Option B: Complete Phase 2**
1. Implement all CLI updates at once
2. Update all report generation
3. Test end-to-end workflow

### 4. Test Commands
```bash
# Load environment
set -a; source .env; set +a

# Run CLI
python -m sdm_tools.cli

# Future: Test refresh
# Should see:
# 1. Refresh All Data → Backup → Normalize → Stats
```

---

## Key Code Snippets

### Email Normalization
```python
from sdm_tools.database.normalize import normalize_email

# Handles AWS SSO, domains, case, numeric suffixes
email = normalize_email("AWSReservedSSO_xxx/Daniel.Quan01@telusinternational.com")
# Returns: "daniel.quan@telus.com"
```

### Query Daily Activity
```python
import sqlite3
conn = sqlite3.connect("data/sdm_tools_normalized_test.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT d.name, das.time_bucket, das.jira_count, das.git_count
    FROM daily_activity_summary das
    JOIN developers d ON das.developer_id = d.id
    WHERE das.activity_date = '2025-11-18'
      AND d.active = 1
    ORDER BY das.total_count DESC
""")

for row in cursor.fetchall():
    print(row)
```

### Query Sprint Activity
```python
cursor.execute("""
    SELECT das.activity_date, d.name, 
           SUM(das.jira_count), SUM(das.git_count)
    FROM daily_activity_summary das
    JOIN developers d ON das.developer_id = d.id
    WHERE das.sprint_id = 163231  -- Sprint 72
      AND d.active = 1
    GROUP BY das.activity_date, d.name
    ORDER BY das.activity_date
""")
```

---

## Dependencies

No new dependencies needed for Phase 2. Current `requirements.txt` has:
- rich
- click  
- requests
- pyfiglet
- (sqlite3 is built-in)

---

## Notes & Decisions

### Email Matching Strategy
- Use normalized email as primary key
- Store all variations in `developer_email_aliases` table
- Auto-detect patterns (AWS SSO, domains, suffixes)
- No manual mapping file needed (all auto-mapped)

### Sprint Assignment
- Events assigned to sprint based on event date falling within sprint date range
- `NULL` sprint_id if date falls outside all sprints
- Pre-calculated during normalization (no runtime lookups)

### Materialization Strategy
- `daily_activity_summary` table pre-aggregates ALL events
- One row per (date, developer, time_bucket) combination
- Dashboard queries this table directly (instant results)
- Rebuild entire table on each data refresh

### Backup Strategy
- Timestamped backups before each refresh
- Keep last 5 backups (configurable)
- Format: `sdm_tools_backup_YYYYMMDD_HHMMSS.db`

---

## Contact & Context

**Project**: SDM-Tools - Daily Activity Reporting  
**Developer**: Juan Gramajo (juan.gramajo@telus.com)  
**Repository**: `/Users/juangramajo/git/telus/playground/sdm-tools`  
**Data Source**: Jira (IOTMI 3P Connector) + Local Git Repo  
**Team Size**: 7 active developers  
**Sprint Cadence**: 2-week sprints  
**Timezone**: America/Mexico_City (GMT-6)

---

## Session End Checklist

Before ending session:
- [x] Phase 1 implementation complete
- [x] All tests passing
- [x] Validation document created
- [x] Session state documented
- [ ] Phase 2 plan documented (this file)
- [ ] Ready to continue in new session

**Next Session**: Start with Phase 2.1 (Database Refresh Workflow)
