"""
EOS Platform - Accountability Chart Routes
Organizational structure with seats and responsibilities
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

def register_accountability_routes(app):
    """Register accountability chart-related routes"""
    
    @app.route('/division/<int:division_id>/accountability')
    @login_required
    @division_access_required('division_id')
    def division_accountability(division_id):
        """View accountability chart for a division"""
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
        
        # Get accountability chart data
        try:
            cursor.execute("""
                SELECT 
                    id, seat_name as seat, person_name as person,
                    role_description, reports_to, level,
                    is_right_person, is_right_seat
                FROM accountability_chart
                WHERE division_id = ? AND is_active = 1
                ORDER BY level, seat_name
            """, (division_id,))
            
            seats = [dict(row) for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            # Accountability chart table doesn't exist yet
            seats = []
        
        # Calculate summary
        total_seats = len(seats)
        filled_seats = len([s for s in seats if s.get('person_name')])
        right_person_right_seat = len([s for s in seats if s.get('is_right_person') and s.get('is_right_seat')])
        
        summary = {
            'total_seats': total_seats,
            'filled': filled_seats,
            'empty': total_seats - filled_seats,
            'right_person_right_seat': right_person_right_seat
        }
        
        conn.close()
        
        can_edit = can_edit_division(user, division_id)
        
        return render_template('accountability.html',
                             user=user,
                             division=division,
                             seats=seats,
                             summary=summary,
                             can_edit=can_edit)
