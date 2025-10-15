# Agent Guidelines for SDM-Tools

## Build/Lint/Test Commands
- **Run CLI**: `python -m sdm_tools.cli`
- **No formal test suite**: No pytest/unittest files exist; manual testing via CLI
- **No linting configured**: No flake8, pylint, black, or ruff config found

## Code Style

### Imports
- Standard library first, third-party second, local imports last
- From-imports for specific functions/classes: `from .config import DB_NAME`
- Import modules for external packages: `import requests`, `import sqlite3`

### Formatting
- **Indentation**: 4 spaces
- **String quotes**: Single quotes for strings, double quotes for JSON/data
- **Line length**: No strict limit observed (~80-120 chars typical)
- **Docstrings**: Triple double-quotes, brief one-liners preferred

### Naming
- **Functions/variables**: snake_case (`fetch_issue_ids`, `all_issues`)
- **Constants**: UPPER_SNAKE_CASE (`JIRA_URL`, `DB_NAME`)
- **Files/modules**: snake_case (`utils.py`, `database/core.py`)

### Error Handling
- Use try-except with Rich console error messages: `console.print(f"[bold red]Error: {str(e)}[/bold red]")`
- Raise exceptions with descriptive messages for API failures
- Always restore state (e.g., `os.chdir(original_cwd)` in finally blocks)
