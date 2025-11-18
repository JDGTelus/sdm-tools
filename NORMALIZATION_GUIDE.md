# Database Normalization Quick Reference Guide

## Overview

This guide provides quick reference for using the normalized database schema and functions.

---

## Key Functions Reference

### Schema Management

```python
from sdm_tools.database.schema import (
    create_normalized_schema,
    drop_all_tables,
    get_table_stats
)

# Create fresh schema
import sqlite3
conn = sqlite3.connect("data/new_db.db")
create_normalized_schema(conn)
conn.close()

# Drop all tables (fresh start)
conn = sqlite3.connect("data/db.db")
drop_all_tables(conn)
conn.close()

# Get table statistics
conn = sqlite3.connect("data/db.db")
stats = get_table_stats(conn)
# Returns: {'developers': 152, 'sprints': 9, ...}
conn.close()
```

### Normalization

```python
from sdm_tools.database.normalize import normalize_all_data

# Full normalization pipeline
stats = normalize_all_data(
    old_db_path="data/sdm_tools.db",
    new_db_path="data/sdm_tools_normalized.db"
)

# Returns dict with:
# {
#     'developers': 152,
#     'sprints': 9,
#     'issues': 218,
#     'jira_events': 636,
#     'git_events': 10919,
#     'summary_rows': 6512,
#     'table_stats': {...}
# }
```

### Email Normalization

```python
from sdm_tools.database.normalize import normalize_email

# Auto-handles AWS SSO, domains, case, suffixes
email1 = normalize_email("AWSReservedSSO_TELUS-IoT-Developer_xxx/daniel.quan@telus.com")
# Returns: "daniel.quan@telus.com"

email2 = normalize_email("Carlos.Carias01@TELUSINTERNATIONAL.COM")
# Returns: "carlos.carias@telus.com"
```

### Developer Lookup

```python
from sdm_tools.database.normalize import find_developer_id_by_email

conn = sqlite3.connect("data/sdm_tools_normalized.db")

# Find developer by any email variation
dev_id = find_developer_id_by_email(conn, "daniel.quan@telusinternational.com")
# Returns: 5 (or None if not found)

conn.close()
```

---

## Common Queries

### Get Active Developers

```sql
SELECT id, email, name
FROM developers
WHERE active = 1
ORDER BY name;
```

### Get Developer Activity Summary

```sql
SELECT 
    d.name,
    COUNT(DISTINCT je.id) as jira_actions,
    COUNT(DISTINCT ge.id) as git_commits,
    COUNT(DISTINCT je.id) + COUNT(DISTINCT ge.id) as total_actions
FROM developers d
LEFT JOIN jira_events je ON d.id = je.developer_id
LEFT JOIN git_events ge ON d.id = ge.developer_id
WHERE d.active = 1
GROUP BY d.id
ORDER BY total_actions DESC;
```

### Get Activity for a Single Day

```sql
SELECT 
    d.name,
    s.name as sprint,
    das.time_bucket,
    das.jira_count,
    das.git_count,
    das.total_count
FROM daily_activity_summary das
JOIN developers d ON das.developer_id = d.id
LEFT JOIN sprints s ON das.sprint_id = s.id
WHERE das.activity_date = '2025-11-18'
  AND d.active = 1
  AND das.total_count > 0
ORDER BY das.total_count DESC;
```

### Get Activity for Entire Sprint

```sql
SELECT 
    das.activity_date,
    d.name,
    SUM(das.jira_count) as jira,
    SUM(das.git_count) as git,
    SUM(das.total_count) as total
FROM daily_activity_summary das
JOIN developers d ON das.developer_id = d.id
WHERE das.sprint_id = 163231  -- Sprint 72
  AND d.active = 1
GROUP BY das.activity_date, d.name
ORDER BY das.activity_date, total DESC;
```

### Get Sprint Summary

```sql
SELECT 
    s.name,
    s.state,
    s.start_date_local,
    s.end_date_local,
    COUNT(DISTINCT d.id) as active_developers,
    SUM(das.jira_count) as total_jira,
    SUM(das.git_count) as total_git,
    SUM(das.total_count) as total_actions
FROM daily_activity_summary das
JOIN developers d ON das.developer_id = d.id
JOIN sprints s ON das.sprint_id = s.id
WHERE d.active = 1
GROUP BY das.sprint_id
ORDER BY s.start_date_local DESC;
```

### Get Activity for Date Range

```sql
SELECT 
    das.activity_date,
    d.name,
    das.time_bucket,
    das.jira_count,
    das.git_count,
    das.total_count
FROM daily_activity_summary das
JOIN developers d ON das.developer_id = d.id
WHERE das.activity_date BETWEEN '2025-11-10' AND '2025-11-15'
  AND d.active = 1
  AND das.total_count > 0
ORDER BY das.activity_date, das.total_count DESC;
```

### Get Time Bucket Distribution

```sql
SELECT 
    time_bucket,
    SUM(total_count) as actions,
    COUNT(DISTINCT developer_id) as developers
FROM daily_activity_summary
WHERE activity_date BETWEEN '2025-11-01' AND '2025-11-18'
GROUP BY time_bucket
ORDER BY 
    CASE time_bucket
        WHEN '8am-10am' THEN 1
        WHEN '10am-12pm' THEN 2
        WHEN '12pm-2pm' THEN 3
        WHEN '2pm-4pm' THEN 4
        WHEN '4pm-6pm' THEN 5
        WHEN 'off_hours' THEN 6
    END;
```

### Get Developer Email Aliases

```sql
SELECT 
    d.email as primary_email,
    d.name,
    GROUP_CONCAT(a.alias_email, ', ') as aliases
FROM developers d
LEFT JOIN developer_email_aliases a ON d.id = a.developer_id
WHERE d.active = 1
GROUP BY d.id
ORDER BY d.name;
```

### Get Most Active Days

```sql
SELECT 
    das.activity_date,
    s.name as sprint,
    COUNT(DISTINCT das.developer_id) as active_devs,
    SUM(das.jira_count) as jira,
    SUM(das.git_count) as git,
    SUM(das.total_count) as total
FROM daily_activity_summary das
LEFT JOIN sprints s ON das.sprint_id = s.id
GROUP BY das.activity_date
ORDER BY total DESC
LIMIT 10;
```

### Get Off-Hours Activity

```sql
SELECT 
    d.name,
    SUM(CASE WHEN das.time_bucket = 'off_hours' THEN das.total_count ELSE 0 END) as off_hours,
    SUM(CASE WHEN das.time_bucket != 'off_hours' THEN das.total_count ELSE 0 END) as regular_hours,
    SUM(das.total_count) as total,
    ROUND(
        100.0 * SUM(CASE WHEN das.time_bucket = 'off_hours' THEN das.total_count ELSE 0 END) / 
        SUM(das.total_count), 
        1
    ) as off_hours_pct
FROM daily_activity_summary das
JOIN developers d ON das.developer_id = d.id
WHERE d.active = 1
  AND das.activity_date >= date('now', '-30 days')
GROUP BY d.id
ORDER BY off_hours_pct DESC;
```

---

## Python Query Helpers (To Be Implemented in Phase 2)

### Example Usage

```python
from sdm_tools.database.stats import (
    query_daily_activity,
    query_sprint_activity,
    query_date_range_activity
)

# Single day
data = query_daily_activity(target_date="2025-11-18")
# Returns: {
#   'developers': [...],
#   'summary': {...},
#   'sprint_context': {...}
# }

# Full sprint
data = query_sprint_activity(sprint_id=163231)
# Returns: {
#   'sprint': {...},
#   'daily_breakdown': [...],
#   'developer_summary': [...],
#   'summary': {...}
# }

# Date range
data = query_date_range_activity(
    start_date="2025-11-10",
    end_date="2025-11-15"
)
# Returns: {
#   'date_range': {...},
#   'daily_breakdown': [...],
#   'sprints_included': [...],
#   'summary': {...}
# }
```

---

## Testing & Validation

### Run Full Test Suite

```bash
cd /Users/juangramajo/git/telus/playground/sdm-tools
python test_normalization.py
```

### Manual Database Inspection

```bash
# Open database
sqlite3 data/sdm_tools_normalized_test.db

# Show all tables
.tables

# Show table schema
.schema developers

# Enable column mode
.mode column
.headers on

# Run any query
SELECT * FROM developers LIMIT 5;

# Exit
.quit
```

### Verify Email Matching

```bash
sqlite3 data/sdm_tools_normalized_test.db << 'EOF'
.mode column
.headers on
SELECT d.email, d.name, COUNT(ge.id) as commits
FROM developers d
LEFT JOIN git_events ge ON d.id = ge.developer_id
WHERE d.active = 1
GROUP BY d.id;
EOF
```

---

## Troubleshooting

### Issue: Developer not showing activity

**Check 1**: Is developer in INCLUDED_EMAILS?
```sql
SELECT email, active FROM developers WHERE email LIKE '%name%';
```

**Check 2**: Check email aliases
```sql
SELECT d.email, a.alias_email 
FROM developers d
JOIN developer_email_aliases a ON d.id = a.developer_id
WHERE d.email LIKE '%name%';
```

**Check 3**: Check raw git commits
```bash
sqlite3 data/sdm_tools.db "SELECT DISTINCT author_email FROM git_commits WHERE author_email LIKE '%name%';"
```

### Issue: Sprint not showing in reports

**Check 1**: Verify sprint exists
```sql
SELECT * FROM sprints WHERE name LIKE '%Sprint%';
```

**Check 2**: Check date ranges
```sql
SELECT id, name, start_date_local, end_date_local FROM sprints ORDER BY start_date_local DESC;
```

**Check 3**: Verify events are assigned to sprint
```sql
SELECT sprint_id, COUNT(*) 
FROM git_events 
GROUP BY sprint_id;
```

### Issue: Time buckets seem wrong

**Check 1**: Verify timezone configuration
```bash
echo $TIMEZONE
# Should be: America/Mexico_City
```

**Check 2**: Check sample events
```sql
SELECT event_timestamp, event_hour, time_bucket 
FROM jira_events 
LIMIT 10;
```

**Check 3**: Verify time bucket logic in utils.py
```python
from sdm_tools.utils import get_time_bucket
from datetime import datetime
from zoneinfo import ZoneInfo

dt = datetime(2025, 11, 18, 10, 30, 0, tzinfo=ZoneInfo('America/Mexico_City'))
bucket = get_time_bucket(dt)
print(bucket)  # Should be: "10am-12pm"
```

---

## Performance Tips

### Use Indexes

All critical queries use indexes. Check with:
```sql
.indexes developers
.indexes daily_activity_summary
```

### Avoid Full Table Scans

Bad:
```sql
SELECT * FROM git_events;  -- 10,919 rows!
```

Good:
```sql
SELECT * FROM git_events WHERE sprint_id = 163231;  -- Uses index
```

### Use Materialized Summary

Bad (slow):
```sql
-- Recalculate from events
SELECT developer_id, COUNT(*) 
FROM git_events 
WHERE commit_date = '2025-11-18'
GROUP BY developer_id;
```

Good (fast):
```sql
-- Query pre-aggregated summary
SELECT developer_id, SUM(git_count)
FROM daily_activity_summary
WHERE activity_date = '2025-11-18'
GROUP BY developer_id;
```

---

## Schema Change Workflow

If you need to modify the schema:

1. **Update schema.py** with new table definition
2. **Update normalize.py** to populate new fields
3. **Drop and recreate test database**:
   ```bash
   rm data/sdm_tools_normalized_test.db
   python test_normalization.py
   ```
4. **Validate changes** with test queries
5. **Update production** via CLI refresh workflow

---

## Backup & Recovery

### Create Backup

```bash
cp data/sdm_tools.db data/sdm_tools_backup_$(date +%Y%m%d_%H%M%S).db
```

### List Backups

```bash
ls -lh data/sdm_tools_backup_*.db
```

### Restore from Backup

```bash
cp data/sdm_tools_backup_20251118_120000.db data/sdm_tools.db
```

---

## Reference Links

- **Session State**: `SESSION_STATE.md`
- **Phase 1 Validation**: `PHASE1_VALIDATION.md`
- **Main README**: `README.md`
- **Schema Code**: `sdm_tools/database/schema.py`
- **Normalization Code**: `sdm_tools/database/normalize.py`
- **Test Script**: `test_normalization.py`
