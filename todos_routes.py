"""
EOS Platform - To-Dos Routes
Action items with owners and due dates
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, division_access_required, division_edit_required, log_action, can_edit_division
import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def get_db():
    """Get database connection with timeout for concurrent access"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def register_todos_routes(app):
    """Register todos-related routes"""
    
    @app.route('/division/<int:division_id>/todos')
    @login_required
    @division_access_required('division_id')
    def division_todos(division_id):
        """View all todos for a division"""
        user = session.get('user')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get division info
        cursor.execute("""
            SELECT d.*, o.name as org_name
            FROM divisions d
            JOIN organizations o ON d.organization_id = o.id
            WHERE d.id = ?
        """, (division_id,))
        division = dict(cursor.fetchone())
        
        # Get all active todos
        cursor.execute("""
            SELECT 
                id, task as todo, owner, due_date, status, priority,
                source, is_completed, completed_at, completed_by,
                created_at, updated_at
            FROM todos
            WHERE division_id = ? AND is_active = 1
            ORDER BY 
                is_completed ASC,
                CASE priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                due_date ASC
        """, (division_id,))
        
        todos = [dict(row) for row in cursor.fetchall()]
        
        # Calculate summary
        total = len(todos)
        open_count = len([t for t in todos if not t.get('is_completed')])
        complete = len([t for t in todos if t.get('is_completed')])
        overdue = len([t for t in todos if t.get('due_date') and t.get('due_date') < datetime.now().strftime('%Y-%m-%d') and not t.get('is_completed')])
        
        summary = {
            'total': total,
            'open': open_count,
            'complete': complete,
            'overdue': overdue
        }
        
        conn.close()
        
        can_edit = can_edit_division(user, division_id)
        
        return render_template('todos.html',
                             user=user,
                             division=division,
                             todos=todos,
                             summary=summary,
                             can_edit=can_edit)
