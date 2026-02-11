#!/usr/bin/env python3
"""
Update passwords for existing users
"""

import sqlite3
from pathlib import Path
from auth import hash_password

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def update_user_passwords():
    """Update passwords for Brian, Kurt, Tammy, and Jeff"""
    
    # Default password for all users (CHANGE IN PRODUCTION!)
    default_password = hash_password("EOS2026!")
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    users = ['brian', 'kurt', 'tammy', 'jeff']
    
    for username in users:
        cursor.execute("""
            UPDATE users 
            SET password_hash = ? 
            WHERE username = ?
        """, (default_password, username))
        print(f"✅ Updated password for: {username}")
    
    conn.commit()
    conn.close()
    
    print("\n⚠️  DEFAULT PASSWORD: EOS2026!")
    print("⚠️  All users can now login with this password")
    print("⚠️  CHANGE PASSWORDS IMMEDIATELY IN PRODUCTION!\n")

if __name__ == '__main__':
    print("Updating user passwords...\n")
    update_user_passwords()
    print("Done!")
