# Sprint Velocity Dashboard - Setup Guide

## 🎯 Overview

The Sprint Velocity Dashboard has been successfully implemented! This feature provides visual analysis of **Planned vs Delivered Story Points** across sprints, helping teams track velocity trends and completion rates.

## 📊 Features

- **Line Chart**: Visual comparison of planned vs delivered points over time
- **Detailed Table**: Sprint-by-sprint breakdown with completion rates
- **Summary Cards**: Overall statistics and averages
- **Color Coding**: Green (high completion), Yellow (medium), Red (needs attention)

## ⚠️ IMPORTANT: Setup Required

Before you can use this feature, you need to complete these steps:

### Step 1: Identify Your Story Points Field

Jira stores story points in custom fields. You need to identify which field your instance uses:

**Option A: Check Jira Board Settings**
1. Go to your Jira board settings
2. Look for "Story Points" or "Estimation" field
3. Note the field ID (usually shows as `customfield_XXXXX`)

**Option B: Test with API** (if you have API access)
```bash
# Fetch a single issue and inspect fields
curl -u your-email@example.com:API_TOKEN \
  "https://your-jira-domain.atlassian.net/rest/api/3/issue/ISSUE-KEY" \
  | jq '.fields | keys | .[]' | grep customfield
```

**Common Story Points Fields:**
- `customfield_10016` (most common for Jira Cloud)
- `customfield_10026`
- `customfield_10002`
- `customfield_10004`

### Step 2: Update normalize.py (if needed)

The code already checks for common story points fields:
- `customfield_10016`
- `customfield_10026`
- `customfield_10002`
- `customfield_10004`

**If your field is different:**

Edit `sdm_tools/database/normalize.py` around line 440:

```python
# Find this section:
for possible_field in ['customfield_10016', 'customfield_10026', 'customfield_10002', 'customfield_10004']:

# Add your field to the list:
for possible_field in ['customfield_10016', 'customfield_10026', 'customfield_YOUR_FIELD']:
```

### Step 3: Run Full Data Refresh

**CRITICAL**: You must run a full data refresh to:
1. Recreate the database with the new `story_points` column
2. Fetch story points from Jira
3. Populate the normalized database

```bash
# From the project root
python -m sdm_tools.cli

# Choose option 1: "Refresh All Data (Jira + Git → Normalize)"
# Confirm with "yes"
# Wait for completion (may take several minutes)
```

This will:
- ✓ Backup your current database
- ✓ Fetch fresh data from Jira with ALL fields (including story points)
- ✓ Create new database schema with `story_points` column
- ✓ Normalize and populate all data

## 📈 Using the Dashboard

### Generate the Report

```bash
python -m sdm_tools.cli

# Choose option 2: "Generate Activity Reports"
# Then choose option 3: "Sprint velocity report (Planned vs Delivered)"
```

This creates: `ux/web/data/sprint_velocity_report.json`

### View the Dashboard

Open in your browser:
```
ux/web/sprint-velocity-dashboard.html
```

**Features:**
- **Summary Cards**: Quick stats at the top
- **Line Chart**: Trend visualization (planned vs delivered)
- **Table**: Detailed sprint-by-sprint breakdown
- **Color Coding**: Visual indicators for completion rates

## 🧪 Testing with Mock Data

Mock data has been created with 9 valid sprints for testing:

```bash
# The mock file is already created at:
ux/web/data/sprint_velocity_report.json

# Open the dashboard to see it working:
# ux/web/sprint-velocity-dashboard.html
```

**Mock Data Features:**
- 9 sprints (Sprint 64-72) - matches available valid sprints
- Oldest sprint on left, newest on right
- Sprint 73 excluded (has NULL dates)
- Data centered at 1/3 chart height
- Chart styling matches sprint-activity-dashboard.html

This lets you preview the dashboard layout and functionality before running the full refresh.

## 📊 Understanding the Metrics

### Planned Points
- **Definition**: Story points for issues assigned to the sprint BEFORE the sprint start date
- **Why**: Provides stable baseline, ignores mid-sprint scope changes
- **Formula**: `SUM(story_points) WHERE created_date < sprint_start_date`

### Delivered Points
- **Definition**: Story points for issues marked as "Done" or "Closed" BY the sprint end date
- **Formula**: `SUM(story_points) WHERE status IN ('Done', 'Closed') AND status_changed_date <= sprint_end_date`

### Completion Rate
- **Formula**: `(Delivered / Planned) * 100`
- **Color Coding**:
  - 🟢 Green: ≥90%
  - 🟡 Yellow: 60-89%
  - 🔴 Red: <60%

## 🔧 Customization

### Adjusting Status Names

If your Jira uses different status names for "completed" work:

Edit `sdm_tools/database/sprint_metrics.py` around line 52:

```python
# Find this line:
WHEN i.status_name IN ('Done', 'Closed')

# Adjust to your status names:
WHEN i.status_name IN ('Done', 'Closed', 'Resolved', 'Completed')
```

### Changing Default Sprint Limit

The report shows last 10 sprints by default. To change:

Edit `sdm_tools/database/reports.py` in the `generate_sprint_velocity_report()` function:

```python
def generate_sprint_velocity_report(limit=10, output_file=None):
    # Change limit=10 to your desired value
```

## 📁 Files Created

### Code Files
- `sdm_tools/database/schema.py` - Added `story_points` column
- `sdm_tools/database/normalize.py` - Extracts story points from Jira
- `sdm_tools/database/sprint_metrics.py` - **NEW**: Velocity calculations
- `sdm_tools/database/reports.py` - Added `generate_sprint_velocity_report()`
- `sdm_tools/cli.py` - Added menu option 3

### Dashboard Files
- `ux/web/sprint-velocity-dashboard.html` - **NEW**: Interactive dashboard
- `ux/web/data/sprint_velocity_report.json` - Generated data file

## 🐛 Troubleshooting

### "no such column: i.story_points"
**Cause**: Database doesn't have story_points column yet  
**Solution**: Run data refresh (Step 3 above)

### "No sprint data available"
**Cause**: No sprints in database or data refresh needed  
**Solution**: Run data refresh to populate sprint data

### All story points showing as 0.0
**Cause**: Story points field not being captured  
**Solutions**:
1. Verify correct customfield in normalize.py
2. Check if your Jira issues actually have story points set
3. Re-run data refresh after fixing field name

### Dashboard shows "Failed to load report data"
**Cause**: JSON file not generated  
**Solution**: Generate the report through CLI option 2 → 3

## 📊 Sample Output

### Console Output
```
Generating Sprint Velocity Report...
✓ Sprint Velocity Report generated: ux/web/data/sprint_velocity_report.json
  Sprints analyzed: 10
  Total Planned: 450.0 points
  Total Delivered: 397.5 points
  Avg Completion Rate: 88.3%
```

### JSON Structure
```json
{
  "generated_at": "2025-11-19T...",
  "report_type": "sprint_velocity",
  "metadata": {
    "sprint_count": 10,
    "total_planned_points": 450.0,
    "total_delivered_points": 397.5,
    "overall_completion_rate": 88.3
  },
  "sprints": [
    {
      "name": "Sprint 72",
      "planned_points": 45.0,
      "delivered_points": 38.0,
      "completion_rate": 84.4,
      ...
    }
  ]
}
```

## ✅ Verification Checklist

After data refresh, verify:

- [ ] Database has `story_points` column: `sqlite3 data/sdm_tools.db "PRAGMA table_info(issues)"`
- [ ] Issues have story points: `sqlite3 data/sdm_tools.db "SELECT COUNT(*) FROM issues WHERE story_points IS NOT NULL"`
- [ ] Report generates successfully via CLI
- [ ] JSON file exists: `ux/web/data/sprint_velocity_report.json`
- [ ] Dashboard opens in browser: `ux/web/sprint-velocity-dashboard.html`
- [ ] Chart displays 9-10 sprints (all valid, NULL dates filtered)
- [ ] Chart shows oldest sprint on LEFT, newest on RIGHT
- [ ] Legend appears on RIGHT side (not top)
- [ ] Data centered at approximately 1/3 chart height
- [ ] Table shows sprint details with newest FIRST

## 🚀 Next Steps

1. **Run data refresh** to populate story points
2. **Generate the report** through CLI
3. **Open the dashboard** to view results
4. **Share with your team** - the HTML file is self-contained

## 💡 Tips

- Run refresh regularly to get latest data
- Compare completion rates across sprints to spot trends
- Use the chart to identify sprint planning patterns
- Share the dashboard HTML file with stakeholders (requires internet for CDN libraries)

## 📞 Support

If you encounter issues:
1. Check this guide's troubleshooting section
2. Verify your Jira story points field name
3. Ensure data refresh completed successfully
4. Check console output for specific error messages

---

**Ready to start?** Run the data refresh and generate your first Sprint Velocity Report! 🎉
