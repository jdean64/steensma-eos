"""
Migrate core EOS tables to multi-tenant schema
Adds organization_id and division_id columns to rocks, issues, todos, scorecard_metrics
"""
import sqlite3

DATABASE_PATH = 'eos_data.db'

def migrate_core_tables():
    """Add multi-tenant columns to core EOS tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("🔄 Migrating core EOS tables to multi-tenant schema...\n")
    
    tables_to_migrate = [
        ('rocks', 'description'),
        ('issues', 'issue'),
        ('todos', 'task'),
        ('scorecard_metrics', 'metric_name')
    ]
    
    for table_name, check_column in tables_to_migrate:
        # Check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if not cursor.fetchone():
            print(f"   ⚠️  Table {table_name} doesn't exist yet - skipping")
            continue
        
        print(f"📋 Migrating table: {table_name}")
        
        # Check current columns
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = {row[1] for row in cursor.fetchall()}
        print(f"   Current columns: {len(columns)}")
        
        # Add organization_id if missing
        if 'organization_id' not in columns:
            print(f"   Adding organization_id...")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN organization_id INTEGER")
            # Set default to 1 (Steensma) for existing records
            cursor.execute(f"UPDATE {table_name} SET organization_id = 1 WHERE organization_id IS NULL")
            print(f"   ✓ Added organization_id")
        else:
            print(f"   ✓ organization_id already exists")
        
        # Add division_id if missing
        if 'division_id' not in columns:
            print(f"   Adding division_id...")
            cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN division_id INTEGER")
            # Set default to 1 (Plainwell) for existing records
            cursor.execute(f"UPDATE {table_name} SET division_id = 1 WHERE division_id IS NULL")
            print(f"   ✓ Added division_id")
        else:
            print(f"   ✓ division_id already exists")
        
        # Check for other missing columns based on the table
        if table_name == 'rocks':
            # Rename description -> rock if needed
            if 'description' in columns and 'rock' not in columns:
                print(f"   Note: 'description' column exists (should be 'rock')")
                # SQLite doesn't support column rename easily, will handle in queries
            
            # Add missing columns for rocks
            missing_rock_columns = {
                'year': 'INTEGER',
                'owner_user_id': 'INTEGER',
                'priority': 'INTEGER DEFAULT 1',
                'created_by': 'INTEGER',
                'updated_by': 'INTEGER'
            }
            for col_name, col_type in missing_rock_columns.items():
                if col_name not in columns:
                    print(f"   Adding {col_name}...")
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
        
        elif table_name == 'issues':
            # Add missing columns for issues
            missing_issue_columns = {
                'category': "TEXT DEFAULT 'ADMINISTRATIVE'",
                'owner_name': 'TEXT',
                'owner_user_id': 'INTEGER',
                'resolved_by': 'INTEGER',
                'created_by': 'INTEGER',
                'updated_by': 'INTEGER',
                'added_from_l10_id': 'INTEGER'
            }
            for col_name, col_type in missing_issue_columns.items():
                if col_name not in columns:
                    print(f"   Adding {col_name}...")
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
        
        elif table_name == 'todos':
            # Rename task -> todo if needed (SQLite limitation, will handle in queries)
            missing_todo_columns = {
                'priority': "TEXT DEFAULT 'MEDIUM'",
                'owner_user_id': 'INTEGER',
                'created_by': 'INTEGER',
                'updated_by': 'INTEGER',
                'source_l10_id': 'INTEGER',
                'source_issue_id': 'INTEGER',
                'completed_by': 'INTEGER',
                'is_completed': 'BOOLEAN DEFAULT 0'
            }
            for col_name, col_type in missing_todo_columns.items():
                if col_name not in columns:
                    print(f"   Adding {col_name}...")
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
        
        print(f"   ✅ {table_name} migration complete\n")
    
    conn.commit()
    
    # Verify migrations
    print("\n📊 Verification:")
    for table_name, _ in tables_to_migrate:
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
        if cursor.fetchone():
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [row[1] for row in cursor.fetchall()]
            has_org = 'organization_id' in columns
            has_div = 'division_id' in columns
            print(f"   {table_name}: organization_id={'✓' if has_org else '✗'}, division_id={'✓' if has_div else '✗'}, total columns: {len(columns)}")
    
    conn.close()
    
    print("\n✅ Core tables migration complete!\n")

if __name__ == '__main__':
    migrate_core_tables()
