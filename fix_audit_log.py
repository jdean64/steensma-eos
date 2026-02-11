"""
Fix audit_log table - add missing multi-tenant columns
"""
import sqlite3

DATABASE_PATH = 'eos_data.db'

def fix_audit_log():
    """Add missing columns to audit_log table"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("🔧 Fixing audit_log table...")
    
    # Check current columns
    cursor.execute("PRAGMA table_info(audit_log)")
    columns = {row[1] for row in cursor.fetchall()}
    print(f"   Current columns: {columns}")
    
    # Add missing columns
    if 'organization_id' not in columns:
        print("   Adding organization_id column...")
        cursor.execute("ALTER TABLE audit_log ADD COLUMN organization_id INTEGER")
        print("   ✓ Added organization_id")
    
    if 'division_id' not in columns:
        print("   Adding division_id column...")
        cursor.execute("ALTER TABLE audit_log ADD COLUMN division_id INTEGER")
        print("   ✓ Added division_id")
    
    if 'user_id' not in columns:
        print("   Adding user_id column...")
        cursor.execute("ALTER TABLE audit_log ADD COLUMN user_id INTEGER")
        print("   ✓ Added user_id")
    
    if 'user_agent' not in columns:
        print("   Adding user_agent column...")
        cursor.execute("ALTER TABLE audit_log ADD COLUMN user_agent TEXT")
        print("   ✓ Added user_agent")
    
    # Rename changed_by -> legacy_changed_by if it exists (for backward compatibility)
    # SQLite doesn't support renaming columns easily, so we'll just keep both
    
    conn.commit()
    
    # Verify changes
    cursor.execute("PRAGMA table_info(audit_log)")
    new_columns = [row[1] for row in cursor.fetchall()]
    print(f"\n   Final columns: {new_columns}")
    
    conn.close()
    
    print("✅ audit_log table fixed!\n")

if __name__ == '__main__':
    fix_audit_log()
