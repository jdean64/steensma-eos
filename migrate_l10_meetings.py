"""
Migrate L10 Meetings to Multi-Tenant Schema
"""
import sqlite3
from datetime import datetime

DATABASE_PATH = 'eos_data.db'

def migrate_l10_meetings():
    """Update l10_meetings table to new multi-tenant schema"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    print("🔄 Migrating L10 meetings to multi-tenant schema...")
    
    # Backup old data if any exists
    cursor.execute("SELECT COUNT(*) FROM l10_meetings")
    old_count = cursor.fetchone()[0]
    
    if old_count > 0:
        print(f"   Found {old_count} existing meetings - backing up...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS l10_meetings_backup AS
            SELECT * FROM l10_meetings
        """)
        print(f"   ✓ Backed up to l10_meetings_backup")
    
    # Drop old table
    cursor.execute("DROP TABLE IF EXISTS l10_meetings")
    print("   ✓ Dropped old l10_meetings table")
    
    # Create new structure
    cursor.execute("""
        CREATE TABLE l10_meetings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            division_id INTEGER NOT NULL,
            
            -- Meeting Details
            meeting_date TEXT NOT NULL,
            meeting_time TEXT,
            frequency TEXT DEFAULT 'WEEKLY',
            duration_minutes INTEGER DEFAULT 90,
            actual_duration_minutes INTEGER,
            
            -- Meeting Status
            status TEXT DEFAULT 'SCHEDULED',
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            
            -- Attendees (JSON array)
            attendees JSON,
            attendee_names JSON,
            
            -- Meeting Notes
            segue_good_news TEXT,
            scorecard_review TEXT,
            rock_review TEXT,
            customer_employee_headlines TEXT,
            
            -- IDS Summary
            issues_discussed JSON,
            todos_created JSON,
            
            -- Recording (future)
            recording_url TEXT,
            transcript_text TEXT,
            
            -- Metadata
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by INTEGER,
            facilitator_user_id INTEGER,
            
            FOREIGN KEY (organization_id) REFERENCES organizations(id),
            FOREIGN KEY (division_id) REFERENCES divisions(id),
            FOREIGN KEY (created_by) REFERENCES users(id),
            FOREIGN KEY (facilitator_user_id) REFERENCES users(id)
        )
    """)
    print("   ✓ Created new l10_meetings table")
    
    # Create l10_sections table
    cursor.execute("DROP TABLE IF EXISTS l10_sections")
    cursor.execute("""
        CREATE TABLE l10_sections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            l10_meeting_id INTEGER NOT NULL,
            
            section_name TEXT NOT NULL,
            section_order INTEGER NOT NULL,
            allocated_minutes INTEGER NOT NULL,
            actual_minutes INTEGER,
            
            status TEXT DEFAULT 'PENDING',
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            
            notes TEXT,
            
            FOREIGN KEY (l10_meeting_id) REFERENCES l10_meetings(id)
        )
    """)
    print("   ✓ Created l10_sections table")
    
    # Create index
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_l10_org_div 
        ON l10_meetings(organization_id, division_id)
    """)
    print("   ✓ Created indexes")
    
    # Migrate old data if any
    if old_count > 0:
        print(f"   Migrating {old_count} old meetings...")
        cursor.execute("""
            INSERT INTO l10_meetings (
                organization_id, division_id, meeting_date, meeting_time,
                status, created_at, updated_at, created_by
            )
            SELECT 
                1 as organization_id,
                1 as division_id,
                meeting_date,
                start_time as meeting_time,
                status,
                created_at,
                updated_at,
                NULL as created_by
            FROM l10_meetings_backup
        """)
        print(f"   ✓ Migrated {cursor.rowcount} meetings")
    
    conn.commit()
    conn.close()
    
    print("✅ L10 meetings migration complete!\n")

if __name__ == '__main__':
    migrate_l10_meetings()
