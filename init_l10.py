#!/usr/bin/env python3
"""Initialize L10 Meeting tables and create upcoming meeting"""

import sqlite3
from datetime import datetime, timedelta

def init_l10_tables(db_path='eos_data.db'):
    """Create L10 meeting tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Execute schema
    with open('l10_schema.sql', 'r') as f:
        cursor.executescript(f.read())
    
    conn.commit()
    conn.close()
    print("✅ L10 tables created")

def create_next_meeting(db_path='eos_data.db', meeting_date='2026-02-11'):
    """Create the next L10 meeting with standard agenda"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create meeting
    cursor.execute('''
        INSERT INTO l10_meetings (meeting_date, team_name, start_time, status, created_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (meeting_date, 'Plainwell Team Lead', '7:30 am', 'SCHEDULED', 'system'))
    
    meeting_id = cursor.lastrowid
    
    # Add agenda items from template
    cursor.execute('SELECT section_name, time_allocated, sort_order, description FROM l10_agenda_templates ORDER BY sort_order')
    agenda_items = cursor.fetchall()
    
    for item in agenda_items:
        cursor.execute('''
            INSERT INTO l10_agenda_items (meeting_id, section_name, time_allocated, sort_order, status)
            VALUES (?, ?, ?, ?, ?)
        ''', (meeting_id, item[0], item[1], item[2], 'PENDING'))
    
    # Pull in last week's incomplete to-dos for review
    cursor.execute('''
        SELECT task, owner FROM todos 
        WHERE status != 'COMPLETE' AND is_active = 1
        ORDER BY due_date
        LIMIT 15
    ''')
    
    todos = cursor.fetchall()
    for todo in todos:
        cursor.execute('''
            INSERT INTO l10_todos_review (meeting_id, todo_text, who, done)
            VALUES (?, ?, ?, 0)
        ''', (meeting_id, todo[0], todo[1]))
    
    # Pull in current issues for discussion
    cursor.execute('''
        SELECT id, issue, priority, owner FROM issues
        WHERE is_active = 1
        ORDER BY CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END
        LIMIT 10
    ''')
    
    issues = cursor.fetchall()
    for issue in issues:
        cursor.execute('''
            INSERT INTO l10_issues_discussed (meeting_id, issue_id, priority, discussed, resolved)
            VALUES (?, ?, ?, 0, 0)
        ''', (meeting_id, issue[0], issue[2]))
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ L10 MEETING CREATED")
    print(f"Meeting ID: {meeting_id}")
    print(f"Date: {meeting_date}")
    print(f"Team: Plainwell Team Lead")
    print(f"Agenda Items: {len(agenda_items)}")
    print(f"To-Dos for Review: {len(todos)}")
    print(f"Issues for Discussion: {len(issues)}")
    
    return meeting_id

if __name__ == '__main__':
    init_l10_tables()
    create_next_meeting(meeting_date='2026-02-11')
