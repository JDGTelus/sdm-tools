# Agent Guidelines for SDM-Tools

## Build/Lint/Test Commands

### Running the Application
- **Run CLI**: `python -m sdm_tools.cli`
- **Load environment**: `set -a; source .env; set +a`
- **Run in virtual env**: `source .venv/bin/activate && python -m sdm_tools.cli`

### Testing
- **No formal test suite**: No pytest/unittest files exist; manual testing via CLI only
- **Manual test workflow**:
  1. Refresh all data (Option 1)
  2. Generate all report types (Option 2 → all suboptions)
  3. Verify HTML outputs in `ux/web/` and `dist/`
  4. Check for console errors or exceptions

### Linting/Formatting
- **No linting configured**: No flake8, pylint, black, or ruff config found
- **Syntax check only**: `python -m py_compile sdm_tools/**/*.py`
- **Recommended setup** (not yet implemented):
  ```bash
  pip install black ruff mypy
  black sdm_tools/
  ruff check sdm_tools/
  mypy sdm_tools/
  ```

## Code Style

### Imports
- **Order**: Standard library first, third-party second, local imports last
- **Style**:
  - From-imports for specific functions/classes: `from .config import DB_NAME`
  - Import modules for external packages: `import requests`, `import sqlite3`
- **Dynamic imports**: Use `from .. import config` instead of `from ..config import DB_NAME` when values may change at runtime

### Formatting
- **Indentation**: 4 spaces (no tabs)
- **String quotes**: Single quotes for strings, double quotes for JSON/data
- **Line length**: No strict limit (~80-120 chars typical, up to 150 acceptable)
- **Docstrings**: Triple double-quotes, brief one-liners preferred
- **Blank lines**: Two blank lines between top-level functions/classes

### Naming
- **Functions/variables**: snake_case (`fetch_issue_ids`, `all_issues`)
- **Constants**: UPPER_SNAKE_CASE (`JIRA_URL`, `DB_NAME`)
- **Classes**: PascalCase (if any added in future)
- **Files/modules**: snake_case (`utils.py`, `database/core.py`)
- **Private functions**: Prefix with underscore (`_internal_helper`)

### Error Handling
- **Console output**: Use Rich console for all user-facing messages
  - Errors: `console.print(f"[bold red]Error: {str(e)}[/bold red]")`
  - Warnings: `console.print(f"[yellow]Warning: {message}[/yellow]")`
  - Success: `console.print(f"[bold green]✓ {message}[/bold green]")`
- **Exceptions**: Raise with descriptive messages for API failures
- **State restoration**: Always restore state in finally blocks (e.g., `os.chdir(original_cwd)`)
- **Database**: Always close connections in finally blocks

### Database Patterns
- **Connection handling**:
  ```python
  conn = sqlite3.connect(DB_NAME)
  cursor = conn.cursor()
  try:
      # Do work
      conn.commit()
  finally:
      conn.close()
  ```
- **Parameterized queries**: Always use `?` placeholders to prevent SQL injection
- **Transactions**: Use explicit commits for write operations
- **Error handling**: Catch specific database exceptions when possible

### HTML/JavaScript (Dashboard Files)
- **React components**: Use functional components with hooks
- **Chart.js**: Initialize in useEffect, cleanup on unmount
- **TailwindCSS**: Use utility classes, avoid inline styles
- **Data fetching**: Use fetch API with error handling
- **Consistency**: All dashboards should have identical header/footer structure

## Development Workflow

### Making Changes

1. **Before changing code**:
   - Read relevant files to understand current implementation
   - Check CHANGES.md for recent modifications
   - Consider impact on database schema

2. **When adding features**:
   - Update all three dashboards if UI changes are needed
   - Regenerate standalone reports after template changes
   - Update both README.md and CHANGES.md

3. **Testing changes**:
   - Run full refresh workflow (Option 1)
   - Generate all report types
   - Verify in browser (both `ux/web/` and `dist/` versions)
   - Check for JavaScript console errors

### Common Gotchas

- **Import issues**: Use `from .. import config` for values that change at runtime
- **Dashboard sync**: Changes to `ux/web/*.html` require regenerating `dist/` files
- **Email normalization**: Test with various email formats (AWS SSO, domain variations)
- **Time zones**: Ensure timezone handling is consistent across modules
- **Bundle generation**: Relies on regex parsing; fragile if HTML structure changes significantly

### Architecture Notes

- **Database first**: All queries start with normalized database
- **Pre-aggregation**: `daily_activity_summary` table is the main query source
- **Active flag**: `developers.active = 1` controls visibility in all reports
- **No real-time**: All data is snapshot-based, no live API calls from dashboards
- **Standalone SPA**: Bundle extracts from standalone reports, not vice versa

## Recommended Improvements

### High Priority
1. Add pytest test suite for core database functions
2. Configure black/ruff for consistent formatting
3. Add type hints and run mypy
4. Better error messages for missing environment variables

### Medium Priority
5. Break down large modules (reports.py > 500 lines)
6. Consolidate configuration validation
7. Add retry logic for Jira API calls
8. Document database schema with ERD

### Low Priority
9. Add CI/CD pipeline
10. Support multiple Jira projects
11. PDF export functionality
12. Dark mode for dashboards
