# Sprint Velocity Dashboard - Troubleshooting Guide

## ⚠️ Common Error: "no such column: i.story_points"

### Symptom
```
sqlite3.OperationalError: no such column: i.story_points
```

### Cause
The database schema doesn't have the `story_points` column yet. This happens when:
1. You're using an old database created before the sprint velocity feature was added
2. You haven't run a data refresh since updating the code

### Solution

**IMPORTANT: You must run a full data refresh to add the story_points column**

#### Step-by-Step Fix:

1. **Run the CLI**:
   ```bash
   python -m sdm_tools.cli
   ```

2. **Choose Option 1**:
   ```
   Choose an option:
   1. Refresh All Data (Jira + Git → Normalize)  ← Select this
   2. Generate Activity Reports
   3. View Sprints
   4. View Active Developers
   5. Exit
   ```

3. **Confirm the refresh**:
   ```
   ⚠️  WARNING: This will refresh ALL data from Jira and Git
      - Current database will be backed up
      - Fresh data will be fetched and normalized
      - This may take several minutes

   Continue? (yes/N): yes  ← Type "yes"
   ```

4. **Wait for completion**:
   - The process will:
     - Backup your current database
     - Fetch fresh data from Jira (with story points)
     - Fetch fresh data from Git
     - Create new normalized schema with `story_points` column
     - Populate all data

5. **Generate the report**:
   - After refresh completes, return to menu
   - Choose Option 2: "Generate Activity Reports"
   - Choose Option 3: "Sprint velocity report"
   - Report will be generated successfully!

---

## 🔍 Why This Happens

The Sprint Velocity Dashboard feature requires the `story_points` column in the `issues` table. This column:
- Was added in the latest update
- Must be populated during data normalization
- Extracts story points from Jira customfields

**The column is NOT automatically added to existing databases.**

You must run a refresh to:
1. Create the new schema with the column
2. Extract story points from Jira API
3. Populate the normalized database

---

## ✅ How to Verify the Fix

After running the refresh, verify the column exists:

```bash
sqlite3 data/sdm_tools.db "PRAGMA table_info(issues)" | grep story_points
```

Expected output:
```
3|story_points|REAL|0||0
```

Check if you have story points data:
```bash
sqlite3 data/sdm_tools.db "SELECT COUNT(*) FROM issues WHERE story_points IS NOT NULL"
```

If you see a number > 0, you're good to go!

---

## 🛡️ Enhanced Error Handling (Now Active)

As of this update, the system now provides helpful guidance when this error occurs:

**Before:**
```
sqlite3.OperationalError: no such column: i.story_points
```

**After:**
```
Error: story_points column not found in issues table.
The database schema needs to be updated.
Please run a full data refresh to add the story_points column:
  1. Go to main menu
  2. Choose option 1: "Refresh All Data"
  3. Confirm with "yes"
This will backup your current database and create a new schema with story points support.
```

---

## 📊 What Gets Updated

During the data refresh, the following changes are made:

### Database Schema
- ✅ `issues` table gets `story_points REAL` column
- ✅ All existing normalized tables are recreated
- ✅ Old database is backed up before changes

### Data Population
- ✅ Story points extracted from Jira customfield
- ✅ Supports multiple customfield formats (10016, 10026, etc.)
- ✅ Handles NULL/missing story points gracefully

### Preserved Data
- ✅ All Jira issues remain
- ✅ All Git commits remain
- ✅ All sprint data remains
- ✅ All developer data remains

---

## 🚨 If You Still Get Errors After Refresh

### Issue: Story points all show as 0.0

**Possible Causes:**
1. Jira issues don't have story points set
2. Wrong customfield is being checked

**Solution:**
1. Verify your Jira issues have story points
2. Check which customfield your Jira instance uses
3. Update `sdm_tools/database/normalize.py` if needed (see SPRINT_VELOCITY_SETUP.md)

### Issue: Refresh fails or times out

**Possible Causes:**
1. Jira API issues
2. Network connectivity
3. Large dataset

**Solution:**
1. Check your Jira API token is valid
2. Verify network connection
3. Try again during off-peak hours
4. Contact support if persistent

---

## 💡 Prevention

To avoid this error in the future:
1. Always run a data refresh when updating code that changes schema
2. Read release notes for schema changes
3. Keep your database up to date with regular refreshes

---

## 📞 Still Having Issues?

If you continue to experience problems:

1. **Check the logs** during data refresh for specific errors
2. **Verify environment variables** are set correctly
3. **Test Jira connectivity** manually
4. **Review SPRINT_VELOCITY_SETUP.md** for detailed setup instructions
5. **Check ITERATION_2_SUMMARY.md** for implementation details

---

## ✅ Quick Reference

| Problem | Solution |
|---------|----------|
| "no such column: i.story_points" | Run full data refresh (Option 1) |
| "No sprint data available" | Run data refresh first |
| All story points show 0.0 | Check Jira customfield configuration |
| Refresh fails | Check API credentials and network |

---

**Last Updated:** November 19, 2024
**Version:** 2.0 (with enhanced error handling)
