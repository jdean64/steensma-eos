"""
EOS Platform - Database schema for lifecycle tracking
Using SQLite for edit capability and audit trails
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def init_database():
    """Initialize SQLite database with tables for lifecycle tracking"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Rocks table with versioning
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NOT NULL,
            owner TEXT NOT NULL,
            status TEXT DEFAULT 'NOT STARTED',
            due_date TEXT,
            progress INTEGER DEFAULT 0,
            quarter TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by TEXT,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Rocks history for lifecycle tracking
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rocks_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rock_id INTEGER NOT NULL,
            field_changed TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            change_note TEXT,
            FOREIGN KEY (rock_id) REFERENCES rocks(id)
        )
    ''')
    
    # Issues table with IDS workflow
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue TEXT NOT NULL,
            priority TEXT DEFAULT 'MEDIUM',
            owner TEXT NOT NULL,
            date_added TEXT,
            status TEXT DEFAULT 'IDENTIFIED',
            ids_stage TEXT DEFAULT 'IDENTIFY',
            discussion_notes TEXT,
            solution TEXT,
            resolved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Issues history for lifecycle
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS issues_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_id INTEGER NOT NULL,
            field_changed TEXT NOT NULL,
            old_value TEXT,
            new_value TEXT,
            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            change_note TEXT,
            FOREIGN KEY (issue_id) REFERENCES issues(id)
        )
    ''')
    
    # To-Dos table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT NOT NULL,
            owner TEXT NOT NULL,
            due_date TEXT,
            status TEXT DEFAULT 'OPEN',
            source TEXT,
            completed_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Scorecard metrics
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS scorecard_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metric TEXT NOT NULL,
            owner TEXT NOT NULL,
            goal TEXT,
            week_1 REAL,
            week_2 REAL,
            week_3 REAL,
            week_4 REAL,
            week_5 REAL,
            week_6 REAL,
            week_7 REAL,
            week_8 REAL,
            week_9 REAL,
            week_10 REAL,
            week_11 REAL,
            week_12 REAL,
            week_13 REAL,
            status TEXT DEFAULT 'YELLOW',
            quarter TEXT,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Audit log for all changes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            table_name TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            changed_by TEXT,
            changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            changes JSON,
            ip_address TEXT
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully")

def migrate_csv_to_db():
    """One-time migration from CSV files to SQLite database"""
    import pandas as pd
    from pathlib import Path
    
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    datasheets_dir = Path(__file__).parent / 'datasheets'
    
    # Migrate Rocks
    rocks_file = datasheets_dir / 'rocks.csv'
    if rocks_file.exists():
        try:
            df = pd.read_csv(rocks_file, delimiter='|')
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO rocks (description, owner, status, due_date, progress, quarter)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('Description', ''),
                    row.get('Owner', ''),
                    row.get('Status', 'NOT STARTED'),
                    row.get('DueDate', ''),
                    int(row.get('Progress', 0)) if pd.notna(row.get('Progress')) else 0,
                    'Q1 2026'
                ))
            print(f"Migrated {len(df)} rocks")
        except Exception as e:
            print(f"Error migrating rocks: {e}")
    
    # Migrate Issues
    issues_file = datasheets_dir / 'issues.csv'
    if issues_file.exists():
        try:
            df = pd.read_csv(issues_file, delimiter='|')
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO issues (issue, priority, owner, date_added, status, ids_stage)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('Issue', ''),
                    row.get('Priority', 'MEDIUM'),
                    row.get('Owner', ''),
                    row.get('DateAdded', ''),
                    row.get('Status', 'OPEN'),
                    'IDENTIFY'
                ))
            print(f"Migrated {len(df)} issues")
        except Exception as e:
            print(f"Error migrating issues: {e}")
    
    # Migrate To-Dos
    todos_file = datasheets_dir / 'todos.csv'
    if todos_file.exists():
        try:
            df = pd.read_csv(todos_file, delimiter='|')
            for _, row in df.iterrows():
                cursor.execute('''
                    INSERT INTO todos (task, owner, due_date, status, source)
                    VALUES (?, ?, ?, ?, ?)
                ''', (
                    row.get('Task', ''),
                    row.get('Owner', ''),
                    row.get('DueDate', ''),
                    row.get('Status', 'OPEN'),
                    row.get('Source', '')
                ))
            print(f"Migrated {len(df)} todos")
        except Exception as e:
            print(f"Error migrating todos: {e}")
    
    conn.commit()
    conn.close()
    print("Migration complete")

if __name__ == '__main__':
    print("Initializing EOS database...")
    init_database()
    print("\nMigrating CSV data...")
    migrate_csv_to_db()
    print("\nDone!")
