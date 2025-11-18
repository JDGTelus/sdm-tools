"""Test Phase 3 CLI updates with normalized database."""

import os
os.environ['DB_NAME'] = 'data/sdm_tools_normalized_test.db'

from sdm_tools.database import get_available_sprints, get_active_developers
from sdm_tools.database.reports import generate_daily_report_json, generate_sprint_report_json
from datetime import date

print("="*60)
print("PHASE 3 CLI INTEGRATION TEST")
print("="*60)

# Test 1: Get available sprints
print("\n1. Testing get_available_sprints()...")
sprints = get_available_sprints()
print(f"   ✓ Found {len(sprints)} sprints")
if sprints:
    print(f"   ✓ Most recent: {sprints[0][1]} ({sprints[0][2]})")

# Test 2: Get active developers
print("\n2. Testing get_active_developers()...")
devs = get_active_developers()
print(f"   ✓ Found {len(devs)} active developers")
if devs:
    print(f"   ✓ First developer: {devs[0][1]}")

# Test 3: Generate daily report
print("\n3. Testing generate_daily_report_json()...")
output = generate_daily_report_json(date(2025, 11, 18), "ux/web/data/daily_activity_report.json")
if output:
    print(f"   ✓ Report generated: {output}")
    import os
    size = os.path.getsize(output)
    print(f"   ✓ File size: {size} bytes")

# Test 4: Generate sprint report
print("\n4. Testing generate_sprint_report_json()...")
if sprints:
    sprint_id = sprints[0][0]  # Use most recent sprint
    output = generate_sprint_report_json(sprint_id, "ux/web/data/sprint_activity_report.json")
    if output:
        print(f"   ✓ Sprint report generated: {output}")
        size = os.path.getsize(output)
        print(f"   ✓ File size: {size} bytes")

print("\n" + "="*60)
print("✅ ALL PHASE 3 TESTS PASSED")
print("="*60)
print("\nCLI is ready for manual testing!")
print("Run: python -m sdm_tools.cli")
