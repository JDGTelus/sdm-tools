"""Test script to validate database normalization."""

import os
import sqlite3
import shutil
from datetime import datetime
from sdm_tools.database.schema import create_normalized_schema, get_table_stats
from sdm_tools.database.normalize import normalize_all_data

# Paths
OLD_DB = "data/sdm_tools.db"
TEST_DB = "data/sdm_tools_normalized_test.db"


def main():
    """Run normalization test."""
    print("=" * 60)
    print("DATABASE NORMALIZATION TEST")
    print("=" * 60)
    
    # Check if old database exists
    if not os.path.exists(OLD_DB):
        print(f"\n❌ Old database not found: {OLD_DB}")
        print("Please run the tool to fetch data first.")
        return
    
    # Remove test database if it exists
    if os.path.exists(TEST_DB):
        print(f"\n🗑️  Removing existing test database: {TEST_DB}")
        os.remove(TEST_DB)
    
    # Create new normalized schema
    print(f"\n📝 Creating normalized schema in: {TEST_DB}")
    conn = sqlite3.connect(TEST_DB)
    create_normalized_schema(conn)
    conn.close()
    
    # Run normalization
    print(f"\n🔄 Normalizing data from {OLD_DB} to {TEST_DB}...")
    print()
    
    stats = normalize_all_data(OLD_DB, TEST_DB)
    
    # Display results
    print("\n" + "=" * 60)
    print("NORMALIZATION TEST RESULTS")
    print("=" * 60)
    
    table_stats = stats.get('table_stats', {})
    
    print("\n📊 Table Statistics:")
    for table, count in sorted(table_stats.items()):
        print(f"  {table:30} {count:>8} rows")
    
    # Test queries
    print("\n🔍 Running test queries...")
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    
    # Test 1: Active developers
    cursor.execute("SELECT COUNT(*) FROM developers WHERE active = 1")
    active_devs = cursor.fetchone()[0]
    print(f"\n  ✓ Active developers: {active_devs}")
    
    # Test 2: Developers with email aliases
    cursor.execute("""
        SELECT d.name, d.email, COUNT(a.alias_email) as alias_count
        FROM developers d
        LEFT JOIN developer_email_aliases a ON d.id = a.developer_id
        WHERE d.active = 1
        GROUP BY d.id
        ORDER BY alias_count DESC
        LIMIT 5
    """)
    print("\n  ✓ Top developers by email aliases:")
    for name, email, alias_count in cursor.fetchall():
        print(f"    {name:25} {email:30} ({alias_count} aliases)")
    
    # Test 3: Recent sprints
    cursor.execute("""
        SELECT id, name, state, start_date_local, end_date_local
        FROM sprints
        ORDER BY start_date_local DESC
        LIMIT 5
    """)
    print("\n  ✓ Recent sprints:")
    for sprint_id, name, state, start, end in cursor.fetchall():
        print(f"    {name:30} {state:10} {start} to {end}")
    
    # Test 4: Activity by sprint
    cursor.execute("""
        SELECT 
            s.name,
            COUNT(DISTINCT d.id) as active_devs,
            SUM(das.jira_count) as jira_actions,
            SUM(das.git_count) as git_actions,
            SUM(das.total_count) as total_actions
        FROM daily_activity_summary das
        JOIN developers d ON das.developer_id = d.id
        JOIN sprints s ON das.sprint_id = s.id
        WHERE d.active = 1
        GROUP BY das.sprint_id
        ORDER BY s.start_date_local DESC
        LIMIT 5
    """)
    print("\n  ✓ Activity by sprint:")
    print(f"    {'Sprint':30} {'Devs':>5} {'Jira':>6} {'Git':>6} {'Total':>7}")
    print("    " + "-" * 60)
    for name, devs, jira, git, total in cursor.fetchall():
        print(f"    {name:30} {devs:>5} {jira:>6} {git:>6} {total:>7}")
    
    # Test 5: Email normalization examples
    cursor.execute("""
        SELECT DISTINCT a.alias_email
        FROM developer_email_aliases a
        WHERE a.alias_email LIKE '%AWSReservedSSO%'
           OR a.alias_email LIKE '%telusinternational%'
        LIMIT 10
    """)
    aws_aliases = cursor.fetchall()
    if aws_aliases:
        print("\n  ✓ Email normalization working (AWS SSO/domain variations detected):")
        for (alias,) in aws_aliases[:3]:
            print(f"    {alias}")
    
    # Test 6: Time bucket distribution
    cursor.execute("""
        SELECT time_bucket, SUM(total_count) as actions
        FROM daily_activity_summary
        GROUP BY time_bucket
        ORDER BY 
            CASE time_bucket
                WHEN '8am-10am' THEN 1
                WHEN '10am-12pm' THEN 2
                WHEN '12pm-2pm' THEN 3
                WHEN '2pm-4pm' THEN 4
                WHEN '4pm-6pm' THEN 5
                WHEN 'off_hours' THEN 6
            END
    """)
    print("\n  ✓ Activity by time bucket:")
    for bucket, actions in cursor.fetchall():
        bar = "█" * min(50, int(actions / 10))
        print(f"    {bucket:12} {actions:>6} {bar}")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ NORMALIZATION TEST COMPLETE")
    print("=" * 60)
    print(f"\n📁 Test database saved at: {TEST_DB}")
    print("   Review the results above to validate the normalization.")
    print()


if __name__ == "__main__":
    main()
