#!/usr/bin/env python3
"""
Add Jeff to the EOS platform user list
"""

import sqlite3
from pathlib import Path
from auth import hash_password

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def add_jeff():
    """Add Jeff as a parent admin user"""
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Check if Jeff already exists
    cursor.execute("SELECT id FROM users WHERE username = 'jeff'")
    if cursor.fetchone():
        print("ℹ️  Jeff already exists, updating password...")
        password_hash = hash_password("EOS2026!")
        cursor.execute("""
            UPDATE users 
            SET password_hash = ?, email = ?, full_name = ?, is_active = 1
            WHERE username = 'jeff'
        """, (password_hash, 'jeff@steensma.com', 'Jeff Dean'))
        user_id = cursor.execute("SELECT id FROM users WHERE username = 'jeff'").fetchone()[0]
    else:
        print("➕ Creating new user: Jeff")
        password_hash = hash_password("EOS2026!")
        cursor.execute("""
            INSERT INTO users (username, email, full_name, password_hash, is_active)
            VALUES ('jeff', 'jeff@steensma.com', 'Jeff Dean', ?, 1)
        """, (password_hash,))
        user_id = cursor.lastrowid
        print(f"   ✓ Created user with ID: {user_id}")
    
    # Get PARENT_ADMIN role id
    cursor.execute("SELECT id FROM roles WHERE name = 'PARENT_ADMIN'")
    parent_admin_role = cursor.fetchone()[0]
    
    # Check if Jeff already has parent admin role
    cursor.execute("""
        SELECT id FROM user_roles 
        WHERE user_id = ? AND role_id = ? AND organization_id IS NULL
    """, (user_id, parent_admin_role))
    
    if not cursor.fetchone():
        print("   Adding PARENT_ADMIN role...")
        cursor.execute("""
            INSERT INTO user_roles (user_id, role_id, organization_id, division_id, is_active)
            VALUES (?, ?, NULL, NULL, 1)
        """, (user_id, parent_admin_role))
        print("   ✓ Added PARENT_ADMIN role")
    else:
        print("   ✓ Already has PARENT_ADMIN role")
    
    conn.commit()
    conn.close()
    
    print(f"""
✅ Jeff is ready!
   Username: jeff
   Password: EOS2026!
   Email: jeff@steensma.com
   Role: Parent Administrator (full access to all divisions)
""")

if __name__ == '__main__':
    print("=" * 60)
    print("Adding Jeff to EOS Platform")
    print("=" * 60)
    print()
    add_jeff()
    print("=" * 60)
