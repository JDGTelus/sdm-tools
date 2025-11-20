# Changelog

All notable changes to SDM-Tools will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Normalized database schema with 8 tables for improved query performance
- Sprint-based filtering and activity tracking
- Email auto-mapping with alias support (handles AWS SSO prefixes, domain variations, numeric suffixes)
- Pre-aggregated daily activity summary for 50-100x faster queries
- New CLI menu with 5 options: Refresh Data, Generate Reports, View Sprints, View Developers, Exit
- Complete database refresh workflow with automatic backups (keeps last 5)
- Multiple report types: daily reports, full sprint reports, bundled SPA
- Silent mode for automated workflows (no user prompts during refresh)
- Rich table formatting with color-coded sprint states
- Comprehensive commit tracking from ALL branches using `git log --all`
- Sprint Activity Dashboard with multi-sprint trend analysis
- Standalone report generation in `dist/` directory
- Bundled SPA report with dynamic navigation sidebar
- Dynamic report discovery and extraction from standalone files

### Changed
- **BREAKING**: Git commit fetching now uses `--all` flag to capture commits from all branches
  - Previously only captured commits from the current HEAD branch
  - Now includes commits from feature branches, remote branches, and all refs
  - Provides complete developer activity tracking regardless of branch
- **BREAKING**: CLI menu structure completely redesigned
  - Old: 4 options (Manage Jira, Manage Git, Daily Report, Exit)
  - New: 5 options (Refresh All Data, Generate Reports, View Sprints, View Developers, Exit)
- Database workflow now uses temporary database for raw data collection
- All database modules now use `config.DB_NAME` dynamically for proper temp database support
- Sprint processing is now explicit rather than automatic (controlled by `silent` parameter)

### Fixed
- Critical: Fixed Python import mechanism issue where `DB_NAME` was imported as a copy instead of a reference
  - Changed `from ..config import DB_NAME` to `from .. import config` in issues.py, sprints.py, commits.py
  - Allows proper database path switching during refresh workflow
- Fixed duplicate sprint processing during data refresh
  - Removed automatic sprint processing from `store_issues_in_db()`
  - Added explicit calls with `silent=True` for automated workflows
- Fixed database reference bug in refresh workflow
  - Now uses `original_db_name` consistently instead of stale module-level `DB_NAME`
  - Properly drops tables from production DB, not from temp DB
- Fixed function execution order in cli.py
  - Moved all Phase 2/3 handler functions before the `cli()` entry point
  - Resolved `NameError: name 'manage_issues_new' is not defined`
- Fixed duplicate React hooks declaration in bundled SPA
  - Removed duplicate `const { useState, ... } = React;` from extracted components
  - Bundle now declares hooks once at top level
  - Resolved "Identifier 'useState' has already been declared" error

### Performance
- Query speed improved by 50-100x through pre-aggregated daily_activity_summary table
- Daily activity queries now execute in ~0.05 seconds (previously ~2-3 seconds)
- Sprint activity queries now execute in ~0.1 seconds (previously ~5-10 seconds)
- Report generation completes in ~0.1-0.2 seconds

### Technical Details
- Normalized schema reduces storage by 95% (from 180+ fields to 8-10 fields per table)
- Email normalization handles:
  - AWS SSO prefix removal: `AWSReservedSSO_*/user@domain.com` → `user@domain.com`
  - Domain normalization: `@telusinternational.com` → `@telus.com`
  - Numeric suffix removal: `user01@domain.com` → `user@domain.com`
  - Case normalization: All emails lowercase
- Developer matching: 100% success rate (all active developers matched between Jira and Git)
- Event-based architecture with time bucket pre-calculation
- Sprint assignment by date during normalization

### Database Schema
New normalized tables:
1. `developers` - Central developer registry with active flag
2. `developer_email_aliases` - Email variations for flexible matching
3. `sprints` - Sprint info with parsed local dates
4. `issues` - Simplified issue tracking (core fields only)
5. `issue_sprints` - Many-to-many issue-sprint relationship
6. `jira_events` - Activity events from Jira with time buckets
7. `git_events` - Commit events with sprint assignment
8. `daily_activity_summary` - Pre-aggregated materialized view

### Migration Notes
- First run of "Refresh All Data" will migrate from old schema to normalized schema
- Old database is backed up automatically before migration
- Temporary database is created during refresh, then cleaned up
- All existing data is preserved and normalized

### Recent Enhancements (November 2025)

#### November 19, 2025 - Complete Team Visibility & UX Homologation

**Zero-Activity Developer Visibility**:
- Daily activity reports now show ALL active developers from INCLUDED_EMAILS
- Backend: Modified `query_daily_activity()` to fetch all active developers first, then overlay activity data
- Frontend: Removed `.filter(d => d.daily_total.total > 0)` from heatmap table and charts
- Result: Developers with zero activity are visible with all-zero stats (not hidden)
- Use case: Managers can see complete team roster daily, identifying who worked and who didn't

**Sprint Velocity Dashboard UX Homologation**:
- Updated header to match daily and sprint activity dashboards
  - Changed from `<header>` with `max-w-7xl` to `<div>` with `gradient-bg` class
  - Title size increased from `text-3xl` to `text-4xl font-bold mb-4`
  - Padding changed from `py-6` to `py-12` for full-width gradient effect
  - Subtitle now `text-xl opacity-90` (consistent with other dashboards)
- Updated footer to match standard pattern
  - Removed `<footer>` with `bg-gray-100 border-t`
  - Now uses simple `<div>` with `mt-16 text-center text-gray-600 pb-8`
  - Added 📈 emoji icon and GitHub link to SDM Tools
- Changed main content from `<main>` with `max-w-7xl` to `<div>` with `container mx-auto px-6`
- All three dashboards now have identical UX patterns

**Technical Details**:
- `reports.py:36-96`: Complete rewrite of developer initialization logic
- `daily-activity-dashboard.html:157,321,328,336`: Removed activity filters
- `sprint-velocity-dashboard.html:414-427,494-509`: Header and footer homologation
- Reports now properly handle edge cases (no activity, all zeros, etc.)

#### Sprint Dashboard Homologation (November 18, 2025)
- Updated sprint dashboard header to match daily dashboard styling
- Full-width gradient header with container wrapper
- Consistent footer with GitHub link and icon
- Proper gray background and spacing throughout

#### Bundled SPA Architecture (November 2025)
- Bundle generation now extracts from standalone reports in `dist/`
- Dynamic discovery of all HTML reports (no hardcoding)
- First report (alphabetically) becomes default landing view
- Extracts data, components, and CSS from standalone files
- Automatic reflection of all updates to standalone reports
- Side navigation with collapsible sidebar
- Single-file portability (~121 KB)
- No external template files needed

#### Report Generation Workflow
1. Generate data (JSON files)
2. Generate standalone reports (dist/*.html)
3. Generate bundle (extracts from standalone files)

Benefits:
- Standalone reports are single source of truth
- Bundle always reflects current standalone state
- Extensible: add reports without code changes
- Maintainable: less code, clearer architecture

## [0.1.0] - 2024 (Historical)

### Added
- Initial release with basic Jira and Git integration
- SQLite database for data persistence
- Daily activity report generation with time buckets
- HTML dashboard with React and Chart.js
- Time-bucketed analysis (2-hour intervals)
- Off-hours tracking (6pm-8am)
- Activity heatmap visualization
- Standalone HTML report

### Features
- Jira issue fetching with JQL queries
- Git commit tracking from current branch
- Rich CLI with pagination
- Email-based developer filtering
- Timezone-aware time buckets

---

**Note**: Version 0.1.0 represents the historical baseline. All improvements listed in [Unreleased] were implemented in the normalization and enhancement project completed November 2025.
