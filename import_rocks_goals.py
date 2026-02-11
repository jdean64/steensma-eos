#!/usr/bin/env python3
"""
Import Rocks, 1-Year Goals, and Issues for Generator and Kalamazoo divisions
"""

import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def import_generator_data():
    """Import Generator division rocks and 1-year goals"""
    print("\n" + "="*70)
    print("IMPORTING GENERATOR DIVISION DATA")
    print("="*70)
    
    conn = get_db()
    cursor = conn.cursor()
    
    division_id = 3  # Generator
    organization_id = 1
    year = 2026
    quarter = 1
    
    # Generator Rocks
    rocks = [
        {
            'description': 'Review phone tree and adjust as needed',
            'owner': 'Tammy',
            'priority': 1
        },
        {
            'description': 'Finish PDF Quote with Financing options, program fees, margins, etc',
            'owner': 'Adam',
            'priority': 2
        },
        {
            'description': 'Finish the Contractor Program and start distribution',
            'owner': 'Adam',
            'priority': 3
        },
        {
            'description': 'Design and begin Service Agreement Initiative to increase agreement customers',
            'owner': 'Jason',
            'priority': 4
        }
    ]
    
    print("\nImporting Generator Rocks...")
    for rock in rocks:
        cursor.execute("""
            INSERT INTO rocks (
                organization_id, division_id, description, owner,
                year, quarter, priority, status, progress, is_active, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            organization_id, division_id, rock['description'], rock['owner'],
            year, quarter, rock['priority'], 'NOT_STARTED', 0, 1, 1
        ))
        print(f"  ✓ Rock {rock['priority']}: {rock['description'][:60]}")
    
    # Update Generator 1-Year Goals in VTO
    one_year_goals = """1. Develop contractor business for Gen division
2. Expand Generator sales and service territory to North and West (Holland, Zeeland, Byron Center and south)
3. Increase Service Agreement participation by 1000 from (4500 to 5500)
4. Develop and execute plan to increase Fleet participation to 25%+
5. Investigate and decide on alternative revenue including Battery Wall, smoke/CO detectors, Ecobee, etc."""
    
    cursor.execute("""
        UPDATE vto
        SET one_year_goals = ?,
            updated_at = datetime('now')
        WHERE division_id = ? AND is_active = 1
    """, (one_year_goals, division_id))
    
    print(f"\n  ✓ Updated 1-Year Goals for Generator")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Generator data imported successfully")
    print("="*70 + "\n")

def import_kalamazoo_data():
    """Import Kalamazoo division rocks, 1-year goals, and issues"""
    print("\n" + "="*70)
    print("IMPORTING KALAMAZOO DIVISION DATA")
    print("="*70)
    
    conn = get_db()
    cursor = conn.cursor()
    
    division_id = 2  # Kalamazoo
    organization_id = 1
    year = 2026
    quarter = 1
    
    # Kalamazoo Rocks
    rocks = [
        {
            'description': 'Get Matt H and Jeff N. on road preseason with commercial guys',
            'owner': 'Jack',
            'priority': 1
        },
        {
            'description': 'Setup Help/Web Support – hire one person to share between departments during the year',
            'owner': 'Ryan',
            'priority': 2
        },
        {
            'description': 'Store Transfers – Parts, Paperwork, and Process',
            'owner': 'Jack',
            'priority': 3
        },
        {
            'description': 'Parts Receiving Process',
            'owner': 'JT',
            'priority': 4
        },
        {
            'description': 'Setup Process Efficiency- John Deere Product (first step)/Product on Sales Floor when needed',
            'owner': 'Ryan',
            'priority': 5
        },
        {
            'description': 'Repair Order Write up\'s – collect more accurate information for Service Shop',
            'owner': 'Mike/JT',
            'priority': 6
        }
    ]
    
    print("\nImporting Kalamazoo Rocks...")
    for rock in rocks:
        cursor.execute("""
            INSERT INTO rocks (
                organization_id, division_id, description, owner,
                year, quarter, priority, status, progress, is_active, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            organization_id, division_id, rock['description'], rock['owner'],
            year, quarter, rock['priority'], 'NOT_STARTED', 0, 1, 1
        ))
        print(f"  ✓ Rock {rock['priority']}: {rock['description'][:60]}")
    
    # Update Kalamazoo 1-Year Goals in VTO
    one_year_goals = """1. Research & execute expanding road sales with Matt H and Jeff N. – commercial and spray applications
2. Research and execute plan to expand John Deere sales including CUTs
3. Research and execute plan to expand extended warranty sales
4. Decide on and train up CSR for Web Support
5. Growth (Road Sales – more people on the ground, and outbound selling via phone and email blasts)
6. Inventory Levels – (Lost Sales, Better on Hand Inventory – both parts and units/wholegoods)
7. Assistant Site Lead Identified"""
    
    cursor.execute("""
        UPDATE vto
        SET one_year_goals = ?,
            updated_at = datetime('now')
        WHERE division_id = ? AND is_active = 1
    """, (one_year_goals, division_id))
    
    print(f"\n  ✓ Updated 1-Year Goals for Kalamazoo (7 goals)")
    
    # Import Kalamazoo Issues
    issues = [
        'Inventory Clean up',
        'Woods Equipment – Dead Stock',
        'Back Order Reporting',
        'CSR Shop Support',
        'Government Sales – successor for Tom Myland',
        'More Service Techs and Training for Techs',
        'CSR Help – better training process for new CSR\'s'
    ]
    
    print("\nImporting Kalamazoo Issues...")
    for i, issue_title in enumerate(issues, 1):
        cursor.execute("""
            INSERT INTO issues (
                organization_id, division_id, issue, owner,
                status, category, priority, is_active, created_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            organization_id, division_id, issue_title, 'Unassigned',
            'OPEN', 'PROCESS', 'MEDIUM', 1, 1
        ))
        print(f"  ✓ Issue {i}: {issue_title}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ Kalamazoo data imported successfully")
    print("="*70 + "\n")

def show_summary():
    """Display summary of imported data"""
    conn = get_db()
    cursor = conn.cursor()
    
    print("\n" + "="*70)
    print("IMPORT SUMMARY")
    print("="*70)
    
    # Rocks summary
    cursor.execute("""
        SELECT d.display_name, COUNT(*) as rock_count
        FROM rocks r
        JOIN divisions d ON r.division_id = d.id
        WHERE r.is_active = 1 AND r.year = 2026 AND r.quarter = 1
        GROUP BY d.id, d.display_name
        ORDER BY d.id
    """)
    
    print("\nQ1 2026 Rocks by Division:")
    for row in cursor.fetchall():
        print(f"  {row['display_name']}: {row['rock_count']} rocks")
    
    # Issues summary
    cursor.execute("""
        SELECT d.display_name, COUNT(*) as issue_count
        FROM issues i
        JOIN divisions d ON i.division_id = d.id
        WHERE i.is_active = 1 AND i.status = 'OPEN'
        GROUP BY d.id, d.display_name
        ORDER BY d.id
    """)
    
    print("\nOpen Issues by Division:")
    for row in cursor.fetchall():
        print(f"  {row['display_name']}: {row['issue_count']} issues")
    
    # VTO 1-Year Goals
    cursor.execute("""
        SELECT d.display_name, LENGTH(v.one_year_goals) as goals_length
        FROM vto v
        JOIN divisions d ON v.division_id = d.id
        WHERE v.is_active = 1 AND d.is_active = 1
        ORDER BY d.id
    """)
    
    print("\n1-Year Goals (VTO):")
    for row in cursor.fetchall():
        if row['goals_length']:
            print(f"  {row['display_name']}: {row['goals_length']} chars")
        else:
            print(f"  {row['display_name']}: Not set")
    
    print("\n" + "="*70 + "\n")
    conn.close()

def main():
    """Main import function"""
    print("\n" + "="*70)
    print("EOS PLATFORM - DATA IMPORT FOR GENERATOR & KALAMAZOO")
    print("="*70)
    
    import_generator_data()
    import_kalamazoo_data()
    show_summary()
    
    print("✅ All data imported successfully!")
    print("\nNote: Print function development in progress for tonight\n")

if __name__ == '__main__':
    main()
