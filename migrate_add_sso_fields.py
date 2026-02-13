#!/usr/bin/env python3
"""
Database Migration: Add SSO Fields
Adds sso_identity, sso_provider, and federated_id columns to users table
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def migrate():
    """Add SSO fields to users table"""
    
    print("=" * 70)
    print("Database Migration: Add SSO Fields")
    print("=" * 70)
    print()
    
    if not DATABASE_PATH.exists():
        print(f"❌ Error: Database not found at {DATABASE_PATH}")
        return False
    
    # Backup database first
    backup_path = DATABASE_PATH.parent / f'eos_data_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
    print(f"Creating backup: {backup_path}")
    
    import shutil
    shutil.copy2(DATABASE_PATH, backup_path)
    print(f"✅ Backup created")
    print()
    
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [row[1] for row in cursor.fetchall()]
        
        migrations_needed = []
        
        if 'sso_identity' not in columns:
            migrations_needed.append(('sso_identity', 'VARCHAR(255)'))
        
        if 'sso_provider' not in columns:
            migrations_needed.append(('sso_provider', 'VARCHAR(50)'))
        
        if 'federated_id' not in columns:
            migrations_needed.append(('federated_id', 'VARCHAR(255)'))
        
        if not migrations_needed:
            print("✅ All SSO columns already exist. No migration needed.")
            return True
        
        print(f"Adding {len(migrations_needed)} column(s) to users table:")
        
        for column_name, column_type in migrations_needed:
            print(f"  - {column_name} {column_type}")
            cursor.execute(f"""
                ALTER TABLE users ADD COLUMN {column_name} {column_type}
            """)
        
        # Create index on sso_identity for faster lookups
        print("  - Creating index on sso_identity")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_sso_identity 
            ON users(sso_identity)
        """)
        
        conn.commit()
        
        print()
        print("=" * 70)
        print("✅ Migration completed successfully!")
        print("=" * 70)
        print()
        print("Users table now supports:")
        print("  - SSO authentication (sso_identity, sso_provider)")
        print("  - Federated identity tracking (federated_id)")
        print("  - Fast SSO lookup (indexed)")
        print()
        print("Backup saved at:")
        print(f"  {backup_path}")
        print()
        
        return True
        
    except Exception as e:
        conn.rollback()
        print()
        print(f"❌ Migration failed: {e}")
        print()
        print("Database was NOT modified. Backup is available at:")
        print(f"  {backup_path}")
        return False
        
    finally:
        conn.close()

if __name__ == '__main__':
    success = migrate()
    exit(0 if success else 1)
