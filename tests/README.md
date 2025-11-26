# SDM-Tools Test Suite

## Overview

This test suite provides comprehensive coverage for the core functionality of SDM-Tools, focusing on:

- **Email normalization** (AWS SSO, domain mapping, edge cases)
- **Database schema** (8-table structure, indexes, foreign keys)
- **Time bucket assignment** (timezone conversion, off-hours detection)
- **Developer data merging** (Jira + Git integration)
- **Sprint velocity calculations** (planned vs delivered metrics)

## Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_email_normalizer.py -v
```

### Run with coverage report
```bash
pytest tests/ --cov=sdm_tools --cov-report=term-missing
```

### Generate HTML coverage report
```bash
pytest tests/ --cov=sdm_tools --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Structure

```
tests/
├── README.md                                    # This file
├── __init__.py
├── test_schema.py                               # Database schema tests
├── test_utils.py                                # Time bucket & timezone tests
├── test_sprint_metrics.py                       # Velocity calculation tests
└── test_normalizers/
    ├── __init__.py
    ├── test_email_normalizer.py                 # Email normalization tests
    └── test_developer_normalizer.py             # Developer merging tests
```

## Coverage Summary

**Current Coverage: 13%** (79 tests, all passing)

### High Coverage Modules
- `email_normalizer.py` - 100% (core transformation logic)
- `config.py` - 100% (environment configuration)
- `schema.py` - 78% (database schema creation)
- `utils.py` - 54% (time bucket utilities)
- `developer_normalizer.py` - 55% (developer merging)

### Low Coverage (Integration/UI Heavy)
- `cli.py` - 0% (interactive menu system, excluded from unit tests)
- `jira.py` - 0% (external API calls, requires mocking)
- `repo.py` - 32% (git operations, requires filesystem)
- `reports.py` - 6% (complex queries, integration testing needed)
- `standalone.py` - 7% (HTML generation, complex regex)

## Test Philosophy

These tests follow a **unit-first** approach:

1. **Pure functions tested exhaustively** (normalizers, utils)
2. **Database logic tested with in-memory SQLite** (schema, queries)
3. **Integration points documented but not yet tested** (Jira API, Git, HTML generation)

## Adding New Tests

### Email Normalization Test
```python
def test_new_email_pattern(self):
    """Test description."""
    assert normalize_email('input@example.com') == 'expected@example.com'
```

### Database Schema Test
```python
def test_new_table_structure(self, in_memory_db):
    """Test description."""
    create_normalized_schema(in_memory_db)
    cursor = in_memory_db.cursor()
    cursor.execute("PRAGMA table_info(new_table)")
    columns = [row[1] for row in cursor.fetchall()]
    assert 'expected_column' in columns
```

### Time Bucket Test
```python
def test_new_time_bucket(self):
    """Test description."""
    dt = datetime(2025, 1, 1, 14, 30, tzinfo=ZoneInfo('UTC'))
    assert get_time_bucket(dt) == '2pm-4pm'
```

## Fixtures

### `in_memory_db`
Creates an empty in-memory SQLite database with the 8-table schema.

**Usage:**
```python
def test_example(self, in_memory_db):
    cursor = in_memory_db.cursor()
    cursor.execute("INSERT INTO developers ...")
    in_memory_db.commit()
```

### `metrics_db`
Creates an in-memory database with sample developers and sprints.

**Usage:**
```python
def test_example(self, metrics_db):
    # Pre-populated with 2 developers and 3 sprints
    cursor = metrics_db.cursor()
    cursor.execute("SELECT * FROM sprints")
```

## Known Limitations

1. **No integration tests** - Jira API and Git operations not tested
2. **No CLI tests** - Interactive menu system excluded
3. **No HTML generation tests** - Complex regex parsing fragile to test
4. **Limited query tests** - `reports.py` needs dedicated integration suite

## Future Improvements

- [ ] Add pytest-mock for Jira API testing
- [ ] Add integration tests with fixtures (sample .git repo)
- [ ] Increase query coverage (reports.py, sprint_metrics.py)
- [ ] Add property-based testing (hypothesis) for normalizers
- [ ] Add performance benchmarks for query optimization
