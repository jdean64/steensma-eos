"""
EOS Platform - Scorecard Routes
Weekly measurables and metrics tracking
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

def register_scorecard_routes(app):
    """Register scorecard-related routes"""
    
    @app.route('/division/<int:division_id>/scorecard')
    @login_required
    @division_access_required('division_id')
    def division_scorecard(division_id):
        """View scorecard for a division"""
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
        
        # Get all active scorecard metrics
        cursor.execute("""
            SELECT *
            FROM scorecard_metrics
            WHERE division_id = ? AND is_active = 1
            ORDER BY id
        """, (division_id,))
        
        metrics = [dict(row) for row in cursor.fetchall()]
        
        # Calculate summary
        total = len(metrics)
        green = len([m for m in metrics if m.get('status') == 'GREEN'])
        yellow = len([m for m in metrics if m.get('status') == 'YELLOW'])
        red = len([m for m in metrics if m.get('status') == 'RED'])
        
        summary = {
            'total': total,
            'green': green,
            'yellow': yellow,
            'red': red
        }
        
        conn.close()
        
        can_edit = can_edit_division(user, division_id)
        
        return render_template('scorecard.html',
                             user=user,
                             division=division,
                             metrics=metrics,
                             summary=summary,
                             can_edit=can_edit)
