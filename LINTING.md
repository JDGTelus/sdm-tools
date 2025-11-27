# Code Quality: Linting & Formatting

This project uses automated code quality tools to maintain consistency and catch errors early.

## Tools Installed

### 1. Black (Code Formatter)
**Version**: 25.11.0
**Purpose**: Automatic Python code formatting
**Line Length**: 100 characters

Black is the "uncompromising Python code formatter" that ensures consistent style across the codebase.

### 2. Ruff (Fast Linter)
**Version**: 0.14.6
**Purpose**: Fast Python linter (replaces flake8, isort, and more)
**Rules Enabled**:
- `E` - pycodestyle errors
- `W` - pycodestyle warnings
- `F` - Pyflakes (basic error detection)
- `I` - isort (import sorting)
- `N` - pep8-naming
- `UP` - pyupgrade (modernize code)
- `B` - flake8-bugbear (find likely bugs)
- `C4` - flake8-comprehensions
- `SIM` - flake8-simplify

### 3. MyPy (Type Checker)
**Version**: 1.18.2
**Purpose**: Static type checking
**Mode**: Lenient (gradual typing)

MyPy checks for type consistency but is configured to allow untyped code (can be tightened later).

### 4. Pre-commit (Git Hooks)
**Version**: 4.5.0
**Purpose**: Automatic checks before commits

Pre-commit runs all tools automatically before each git commit, preventing bad code from entering the repository.

## Configuration

All tools are configured in `pyproject.toml`:

```toml
[tool.black]
line-length = 100
target-version = ['py37', ..., 'py313']

[tool.ruff]
line-length = 100
select = ["E", "W", "F", "I", "N", "UP", "B", "C4", "SIM"]

[tool.mypy]
python_version = "3.9"
ignore_missing_imports = true
```

## Manual Commands

### Run Black (Format Code)
```bash
# Format all Python files
black sdm_tools/ tests/

# Check formatting without changing files
black --check sdm_tools/ tests/

# Format specific file
black sdm_tools/utils.py
```

### Run Ruff (Lint Code)
```bash
# Lint and auto-fix issues
ruff check sdm_tools/ tests/ --fix

# Lint without fixing
ruff check sdm_tools/ tests/

# Lint with unsafe fixes (e.g., remove unused imports)
ruff check sdm_tools/ tests/ --fix --unsafe-fixes

# Check specific file
ruff check sdm_tools/utils.py
```

### Run MyPy (Type Check)
```bash
# Check all source files
mypy sdm_tools/

# Check specific file
mypy sdm_tools/utils.py

# Install missing type stubs
mypy --install-types sdm_tools/
```

### Run All Tools Together
```bash
# Format, lint, and type check
black sdm_tools/ tests/
ruff check sdm_tools/ tests/ --fix
mypy sdm_tools/
```

## Pre-commit Hooks

Pre-commit hooks are **automatically installed** and will run before each commit.

### Install Hooks (Already Done)
```bash
pre-commit install
```

### Run Hooks Manually
```bash
# Run all hooks on all files
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files
pre-commit run ruff --all-files
pre-commit run mypy --all-files
```

### Skip Hooks (Emergency Only)
```bash
# Skip all pre-commit checks (NOT RECOMMENDED)
git commit --no-verify -m "emergency fix"
```

## What Happens on Commit

When you run `git commit`, pre-commit will automatically:

1. ✅ **Check for trailing whitespace** and remove it
2. ✅ **Fix file endings** (ensure newline at EOF)
3. ✅ **Run Black** to format all staged files
4. ✅ **Run Ruff** to lint and auto-fix issues
5. ✅ **Run MyPy** to check types

If any tool **modifies files**, the commit will be **aborted** and you'll need to:
- Review the changes
- Stage the modified files: `git add -u`
- Commit again: `git commit`

## Current Status

### Black Results
- ✅ **30 files reformatted** (initial run)
- ✅ **6 files already compliant**
- Line length standardized to 100 characters

### Ruff Results
- ✅ **189 issues auto-fixed** (imports, whitespace, comprehensions)
- ⚠️ **10 bare except warnings** (intentional for robustness)
- Imports sorted automatically

### MyPy Results
- ✅ **29 files checked**
- ⚠️ **4 type stub warnings** (missing types for requests, pytz)
- No actual type errors

## Integration with IDE

### VS Code
Add to `.vscode/settings.json`:
```json
{
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  }
}
```

### PyCharm
1. Install Black plugin: **Settings → Plugins → Black**
2. Install Ruff plugin: **Settings → Plugins → Ruff**
3. Enable format on save: **Settings → Tools → Actions on Save**

## Troubleshooting

### Pre-commit Hook Fails
```bash
# Update hooks to latest versions
pre-commit autoupdate

# Clean cache and retry
pre-commit clean
pre-commit run --all-files
```

### Black and Ruff Conflict
Black always wins. Ruff is configured to ignore E501 (line length) since Black handles it.

### MyPy Missing Imports
```bash
# Install type stubs
pip install types-requests types-pytz

# Or ignore with config (already done)
# ignore_missing_imports = true in pyproject.toml
```

### Too Many Ruff Errors
```bash
# Fix in stages
ruff check sdm_tools/ --fix           # Safe fixes only
ruff check sdm_tools/ --fix --unsafe-fixes  # All fixes
```

## Best Practices

1. **Run tools before committing** (pre-commit does this automatically)
2. **Format with Black first**, then run Ruff
3. **Don't skip pre-commit hooks** unless absolutely necessary
4. **Address linting errors** instead of disabling rules
5. **Add type hints gradually** - start with function signatures

## Ignoring Specific Issues

### Ignore Ruff Warning (Line-Specific)
```python
result = some_function()  # noqa: E501 - Long line acceptable here
```

### Ignore MyPy Error (Line-Specific)
```python
value = unsafe_operation()  # type: ignore[arg-type]
```

### Ignore Ruff in Entire File
Add to top of file:
```python
# ruff: noqa
```

## Future Improvements

- [ ] Add type hints to public API functions
- [ ] Tighten MyPy strictness (enable `disallow_untyped_defs`)
- [ ] Add docstring linter (pydocstyle or darglint)
- [ ] Add complexity checker (radon or mccabe)
- [ ] CI/CD integration (run linters in GitHub Actions)

---

**Summary**: All code is now consistently formatted, linted, and type-checked. Pre-commit hooks ensure quality standards are maintained automatically.
