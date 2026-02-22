"""
EOS Platform - Vision/VTO Routes
Vision/Traction Organizer: 10-year target, 3-year picture, 1-year plan
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, division_access_required, division_edit_required, log_action, can_edit_division
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def get_db():
    """Get database connection with timeout for concurrent access"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA busy_timeout=30000')
    return conn

def register_vision_routes(app):
    """Register vision/VTO-related routes"""
    
    @app.route('/division/<int:division_id>/vision')
    @login_required
    @division_access_required('division_id')
    def division_vision(division_id):
        """View vision/VTO for a division"""
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
        
        # Get VTO data
        cursor.execute("""
            SELECT *
            FROM vto
            WHERE division_id = ? AND is_active = 1
            ORDER BY updated_at DESC
            LIMIT 1
        """, (division_id,))
        
        vto_row = cursor.fetchone()
        vto = None
        core_values = []
        
        if vto_row:
            vto = dict(vto_row)
            # Parse JSON core_values
            try:
                if vto.get('core_values'):
                    core_values = json.loads(vto['core_values'])
            except:
                core_values = []
        
        conn.close()
        
        can_edit = can_edit_division(user, division_id)
        
        return render_template('vision.html',
                             user=user,
                             division=division,
                             vto=vto,
                             core_values=core_values,
                             can_edit=can_edit)
