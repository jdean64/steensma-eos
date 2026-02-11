#!/usr/bin/env python3
"""
EOS Platform Multi-Tenant Database Initialization
Migrates existing single-tenant EOS data to new multi-tenant schema
"""

import sqlite3
import sys
from pathlib import Path
import json
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'
OLD_DATABASE_PATH = Path(__file__).parent / 'eos_data_backup.db'
SCHEMA_PATH = Path(__file__).parent / 'multi_tenant_schema.sql'

def backup_existing_database():
    """Backup existing database before migration"""
    if DATABASE_PATH.exists():
        import shutil
        backup_name = f"eos_data_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = Path(__file__).parent / backup_name
        shutil.copy(DATABASE_PATH, backup_path)
        print(f"✅ Backed up existing database to: {backup_path}")
        return backup_path
    return None

def get_old_data():
    """Extract data from old schema before it's replaced"""
    if not DATABASE_PATH.exists():
        print("ℹ️  No existing database found. Creating fresh database.")
        return None
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    data = {
        'rocks': [],
        'issues': [],
        'todos': [],
        'scorecard': []
    }
    
    # Check if old tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    existing_tables = [row[0] for row in cursor.fetchall()]
    
    print(f"📊 Found existing tables: {', '.join(existing_tables)}")
    
    # Extract rocks
    if 'rocks' in existing_tables:
        cursor.execute("SELECT * FROM rocks WHERE is_active = 1")
        data['rocks'] = [dict(row) for row in cursor.fetchall()]
        print(f"   - Extracted {len(data['rocks'])} rocks")
    
    # Extract issues
    if 'issues' in existing_tables:
        cursor.execute("SELECT * FROM issues WHERE is_active = 1")
        data['issues'] = [dict(row) for row in cursor.fetchall()]
        print(f"   - Extracted {len(data['issues'])} issues")
    
    # Extract todos
    if 'todos' in existing_tables:
        cursor.execute("SELECT * FROM todos WHERE is_active = 1")
        data['todos'] = [dict(row) for row in cursor.fetchall()]
        print(f"   - Extracted {len(data['todos'])} todos")
    
    # Extract scorecard
    if 'scorecard_metrics' in existing_tables:
        cursor.execute("SELECT * FROM scorecard_metrics WHERE is_active = 1")
        data['scorecard'] = [dict(row) for row in cursor.fetchall()]
        print(f"   - Extracted {len(data['scorecard'])} scorecard metrics")
    
    conn.close()
    return data

def initialize_schema():
    """Execute the multi-tenant schema SQL"""
    print("\n🏗️  Initializing multi-tenant schema...")
    
    # Read schema file
    with open(SCHEMA_PATH, 'r') as f:
        schema_sql = f.read()
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Execute schema (split by semi-colons to handle multiple statements)
    statements = schema_sql.split(';')
    for statement in statements:
        statement = statement.strip()
        if statement:
            try:
                cursor.execute(statement)
            except sqlite3.Error as e:
                # Ignore "already exists" errors during development
                if "already exists" not in str(e):
                    print(f"⚠️  Warning executing statement: {e}")
    
    conn.commit()
    conn.close()
    print("✅ Schema initialized successfully")

def migrate_old_data(old_data):
    """Migrate old single-tenant data to new multi-tenant structure"""
    if not old_data:
        print("\nℹ️  No old data to migrate")
        return
    
    print("\n📦 Migrating existing data to multi-tenant structure...")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get Steensma organization and Plainwell division IDs
    cursor.execute("SELECT id FROM organizations WHERE slug = 'steensma'")
    org = cursor.fetchone()
    org_id = org[0] if org else 1
    
    cursor.execute("SELECT id FROM divisions WHERE slug = 'plainwell'")
    div = cursor.fetchone()
    div_id = div[0] if div else 1
    
    print(f"   Migrating to: Organization ID {org_id}, Division ID {div_id}")
    
    # Migrate rocks
    migrated_rocks = 0
    for rock in old_data.get('rocks', []):
        try:
            cursor.execute("""
                INSERT INTO rocks (
                    organization_id, division_id, description, owner_name,
                    status, due_date, progress, quarter, year, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                org_id, div_id,
                rock.get('description', ''),
                rock.get('owner', ''),
                rock.get('status', 'NOT STARTED'),
                rock.get('due_date', ''),
                rock.get('progress', 0),
                rock.get('quarter', 'Q1 2026'),
                2026,
                rock.get('created_at', datetime.now()),
                rock.get('updated_at', datetime.now())
            ))
            migrated_rocks += 1
        except Exception as e:
            print(f"   ⚠️  Warning migrating rock: {e}")
    
    if migrated_rocks > 0:
        print(f"   ✅ Migrated {migrated_rocks} rocks")
    
    # Migrate issues
    migrated_issues = 0
    for issue in old_data.get('issues', []):
        try:
            cursor.execute("""
                INSERT INTO issues (
                    organization_id, division_id, issue, priority, owner_name,
                    date_added, status, ids_stage, discussion_notes, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                org_id, div_id,
                issue.get('issue', ''),
                issue.get('priority', 'MEDIUM'),
                issue.get('owner', ''),
                issue.get('date_added', ''),
                issue.get('status', 'OPEN'),
                issue.get('ids_stage', 'IDENTIFY'),
                issue.get('discussion_notes', ''),
                issue.get('created_at', datetime.now()),
                issue.get('updated_at', datetime.now())
            ))
            migrated_issues += 1
        except Exception as e:
            print(f"   ⚠️  Warning migrating issue: {e}")
    
    if migrated_issues > 0:
        print(f"   ✅ Migrated {migrated_issues} issues")
    
    # Migrate todos
    migrated_todos = 0
    for todo in old_data.get('todos', []):
        try:
            cursor.execute("""
                INSERT INTO todos (
                    organization_id, division_id, task, owner_name,
                    due_date, status, source, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                org_id, div_id,
                todo.get('task', ''),
                todo.get('owner', ''),
                todo.get('due_date', ''),
                todo.get('status', 'OPEN'),
                todo.get('source', ''),
                todo.get('created_at', datetime.now()),
                todo.get('updated_at', datetime.now())
            ))
            migrated_todos += 1
        except Exception as e:
            print(f"   ⚠️  Warning migrating todo: {e}")
    
    if migrated_todos > 0:
        print(f"   ✅ Migrated {migrated_todos} todos")
    
    # Migrate scorecard
    migrated_metrics = 0
    for metric in old_data.get('scorecard', []):
        try:
            cursor.execute("""
                INSERT INTO scorecard_metrics (
                    organization_id, division_id, metric_name, owner_name, goal,
                    week_1, week_2, week_3, week_4, week_5, week_6, week_7,
                    week_8, week_9, week_10, week_11, week_12, week_13,
                    status, quarter, year
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                org_id, div_id,
                metric.get('metric', ''),
                metric.get('owner', ''),
                metric.get('goal', ''),
                metric.get('week_1'), metric.get('week_2'), metric.get('week_3'),
                metric.get('week_4'), metric.get('week_5'), metric.get('week_6'),
                metric.get('week_7'), metric.get('week_8'), metric.get('week_9'),
                metric.get('week_10'), metric.get('week_11'), metric.get('week_12'),
                metric.get('week_13'),
                metric.get('status', 'YELLOW'),
                metric.get('quarter', 'Q1 2026'),
                2026
            ))
            migrated_metrics += 1
        except Exception as e:
            print(f"   ⚠️  Warning migrating scorecard metric: {e}")
    
    if migrated_metrics > 0:
        print(f"   ✅ Migrated {migrated_metrics} scorecard metrics")
    
    conn.commit()
    conn.close()

def create_default_users():
    """Create default admin users with hashed passwords"""
    print("\n👥 Setting up default users...")
    
    from auth import hash_password
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if users already exist
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    
    if user_count > 0:
        print(f"   ℹ️  Users already exist ({user_count} users). Skipping user creation.")
        conn.close()
        return
    
    # Create default password (CHANGE THIS IN PRODUCTION!)
    default_password = hash_password("EOS2026!")
    
    # Create parent admin users
    users = [
        ('brian', 'brian@steensma.com', 'Brian Steensma'),
        ('kurt', 'kurt@steensma.com', 'Kurt Steensma'),
        ('tammy', 'tammy@steensma.com', 'Tammy')
    ]
    
    for username, email, full_name in users:
        cursor.execute("""
            INSERT INTO users (username, email, full_name, password_hash)
            VALUES (?, ?, ?, ?)
        """, (username, email, full_name, default_password))
        print(f"   ✅ Created user: {username} ({email})")
    
    conn.commit()
    conn.close()
    
    print("\n   ⚠️  DEFAULT PASSWORD: EOS2026!")
    print("   ⚠️  CHANGE PASSWORDS IMMEDIATELY IN PRODUCTION!")

def verify_installation():
    """Verify the database was set up correctly"""
    print("\n🔍 Verifying installation...")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]
    
    expected_tables = [
        'organizations', 'divisions', 'users', 'roles', 'user_roles',
        'vto', 'rocks', 'scorecard_metrics', 'issues', 'todos',
        'l10_meetings', 'l10_sections', 'accountability_chart',
        'rocks_history', 'issues_history', 'audit_log'
    ]
    
    missing_tables = [t for t in expected_tables if t not in tables]
    
    if missing_tables:
        print(f"   ⚠️  Missing tables: {', '.join(missing_tables)}")
    else:
        print(f"   ✅ All {len(expected_tables)} expected tables found")
    
    # Check organizations
    cursor.execute("SELECT COUNT(*) FROM organizations")
    org_count = cursor.fetchone()[0]
    print(f"   ✅ Organizations: {org_count}")
    
    # Check divisions
    cursor.execute("SELECT COUNT(*) FROM divisions")
    div_count = cursor.fetchone()[0]
    print(f"   ✅ Divisions: {div_count}")
    
    # Check users
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"   ✅ Users: {user_count}")
    
    # Check rocks
    cursor.execute("SELECT COUNT(*) FROM rocks WHERE is_active = 1")
    rock_count = cursor.fetchone()[0]
    print(f"   ✅ Rocks: {rock_count}")
    
    # Check issues
    cursor.execute("SELECT COUNT(*) FROM issues WHERE is_active = 1")
    issue_count = cursor.fetchone()[0]
    print(f"   ✅ Issues: {issue_count}")
    
    conn.close()
    print("\n✅ Installation verification complete!")

def main():
    """Main migration script"""
    print("=" * 60)
    print("EOS PLATFORM - MULTI-TENANT DATABASE INITIALIZATION")
    print("=" * 60)
    
    # Step 1: Backup existing database
    backup_path = backup_existing_database()
    
    # Step 2: Extract old data before schema change
    old_data = get_old_data()
    
    # Step 3: Initialize new schema
    initialize_schema()
    
    # Step 4: Migrate old data to new structure
    migrate_old_data(old_data)
    
    # Step 5: Create default users
    create_default_users()
    
    # Step 6: Verify installation
    verify_installation()
    
    print("\n" + "=" * 60)
    print("✅ MIGRATION COMPLETE!")
    print("=" * 60)
    
    if backup_path:
        print(f"\n💾 Backup saved: {backup_path}")
    
    print("\n📝 Next Steps:")
    print("   1. Update app.py to use new multi-tenant schema")
    print("   2. Create login/authentication routes")
    print("   3. Build parent dashboard for division selection")
    print("   4. Test with admin users (password: EOS2026!)")
    print("   5. CHANGE DEFAULT PASSWORDS!")
    print("\n")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error during migration: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
