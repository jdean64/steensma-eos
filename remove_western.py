"""
Remove Western division - set to inactive
"""

import sqlite3
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def remove_western():
    """Deactivate Western division"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Deactivate Western division (id=4)
    cursor.execute("""
        UPDATE divisions 
        SET is_active = 0,
            updated_at = datetime('now')
        WHERE id = 4 AND name = 'Western'
    """)
    
    print(f"Deactivated Western division - {cursor.rowcount} row(s) updated")
    
    # Show remaining active divisions
    cursor.execute("""
        SELECT id, name, display_name
        FROM divisions
        WHERE is_active = 1
        ORDER BY id
    """)
    
    print("\nActive divisions:")
    print("-" * 60)
    for row in cursor.fetchall():
        print(f"ID: {row[0]}, Name: {row[1]}, Display: {row[2]}")
    
    conn.commit()
    conn.close()
    print("\n✓ Western division removed successfully")

if __name__ == '__main__':
    remove_western()
