# SDM-Tools Simplified - Quick Start Guide

## 🚀 Get Started in 3 Steps

### Step 1: Install Dependencies
```bash
cd /Users/juangramajo/git/telus/playground/sdm-tools
pip install jinja2 pytz
```

### Step 2: Run Simplified CLI
```bash
# Load environment
set -a; source .env; set +a

# Run CLI
python -m sdm_tools.cli_simple
```

### Step 3: Generate Report
```
Menu:
1. Refresh Data (Incremental) ← Select this first (creates DB)
2. Refresh Data (Full)
3. Generate Bundle Report    ← Then select this
4. Exit
```

Output: `dist/bundle.html` - Open in browser!

---

## 📁 New Files Created

```
templates/
├── bundle.html.j2              # Main Jinja2 template
├── components/
│   ├── daily-dashboard.jsx     # Daily activity React component
│   └── sidebar.jsx             # Navigation component
└── styles/
    └── dashboard.css           # Shared CSS

sdm_tools/
├── database/
│   ├── schema_simple.py        # 3-table schema
│   ├── simple_utils.py         # Email normalization, time bucketing
│   ├── ingest.py               # Upsert logic (Jira + Git)
│   ├── queries.py              # Query functions
│   └── refresh_simple.py       # Incremental refresh workflow
├── cli_simple.py               # New simplified CLI
└── generate.py                 # Jinja2 bundle generation

requirements.txt                # Updated (added jinja2, pytz)
```

---

## 🎯 What's Different?

### Database
- **Before**: 8 tables, complex JOINs
- **After**: 3 tables, single-table queries

### Data Refresh
- **Before**: Always full refresh (5-10 min)
- **After**: Incremental updates (10-30 sec)

### Bundle Generation
- **Before**: HTML → JSON → Regex extraction → Bundle
- **After**: DB → Query → Jinja2 → Bundle

### Code
- **Before**: ~5,000 lines
- **After**: ~1,800 lines (64% reduction)

---

## ✅ What Stays the Same

- ✅ Same visual appearance
- ✅ Same SPA navigation
- ✅ Same charts and metrics
- ✅ Same single-file bundle
- ✅ SQLite storage
- ✅ Jira + Git integration

---

## 🧪 Test with Sample Data

```bash
# Generate test bundle (no DB needed)
python -m sdm_tools.generate

# Opens: dist/bundle_test.html
open dist/bundle_test.html
```

---

## 📊 Database Schema

```sql
-- 1. Developers (email as PK)
CREATE TABLE developers (
    email TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    active BOOLEAN DEFAULT 1
);

-- 2. Activity Events (unified Jira + Git)
CREATE TABLE activity_events (
    id INTEGER PRIMARY KEY,
    developer_email TEXT,
    event_type TEXT,          -- 'jira_create', 'jira_update', 'commit'
    event_timestamp TEXT,
    event_date DATE,
    sprint_name TEXT,         -- Denormalized
    issue_key TEXT,
    commit_hash TEXT UNIQUE,
    metadata TEXT             -- JSON blob
);

-- 3. Sprints
CREATE TABLE sprints (
    name TEXT PRIMARY KEY,
    state TEXT,
    start_date DATE,
    end_date DATE,
    total_planned_points REAL,
    total_delivered_points REAL
);
```

---

## 🔄 Incremental Updates

### How It Works

**Jira**:
```python
# First run: Fetch all
JQL = "project = 'SET' AND component = 'IOTMI'"

# Subsequent runs: Fetch only updated
JQL = "...AND updated >= '2025-11-25T10:30:00Z'"
```

**Git**:
```bash
# First run: Fetch all
git log --all

# Subsequent runs: Fetch only new
git log abc123..HEAD --all
```

---

## 🐛 Troubleshooting

### "No module named 'jinja2'"
```bash
pip install jinja2 pytz
```

### "No database found"
- Run "Refresh Data" from CLI (option 1 or 2)
- Creates database automatically

### "No daily data available"
1. Ensure .env is configured (JIRA_URL, JIRA_API_TOKEN, etc.)
2. Run "Refresh Data" first
3. Check console for errors

### Bundle looks different
- Verify templates/components/ files exist
- Check templates/styles/dashboard.css
- Compare with dist/bundle_test.html

---

## 📖 More Information

- **MIGRATION.md**: Complete migration guide
- **IMPLEMENTATION_SUMMARY.md**: Technical details
- **AGENTS.md**: Development guidelines
- **README.md**: Original documentation

---

## 💡 Pro Tips

1. **Start fresh**: Remove old database, let CLI create new one
2. **Use incremental**: Much faster than full refresh
3. **Test template**: Run `python -m sdm_tools.generate` to verify
4. **Check logs**: Console shows detailed progress
5. **Backup data**: Old system still works if needed

---

**Ready to go!** 🚀

Run: `python -m sdm_tools.cli_simple`
