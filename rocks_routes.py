"""
EOS Platform - Rocks Routes
Quarterly priorities and goals (90-day rocks)
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, division_access_required, division_edit_required, log_action, can_edit_division
import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def register_rocks_routes(app):
    """Register rocks-related routes"""
    
    @app.route('/division/<int:division_id>/rocks')
    @login_required
    @division_access_required('division_id')
    def division_rocks(division_id):
        """View all rocks for a division"""
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
        
        # Get all active rocks
        cursor.execute("""
            SELECT 
                id, description, owner, status, due_date, 
                progress, quarter, year, priority,
                updated_at, updated_by, created_at
            FROM rocks
            WHERE division_id = ? AND is_active = 1
            ORDER BY 
                year DESC,
                quarter DESC,
                CASE priority WHEN 1 THEN 1 WHEN 2 THEN 2 WHEN 3 THEN 3 ELSE 4 END,
                status ASC
        """, (division_id,))
        
        rocks = [dict(row) for row in cursor.fetchall()]
        
        # Calculate summary metrics
        total = len(rocks)
        complete = len([r for r in rocks if r['status'] == 'COMPLETE'])
        on_track = len([r for r in rocks if r['status'] in ['COMPLETE', 'ON_TRACK']])
        at_risk = len([r for r in rocks if r['status'] in ['AT_RISK', 'BLOCKED']])
        not_started = len([r for r in rocks if r['status'] == 'NOT_STARTED'])
        
        summary = {
            'total': total,
            'complete': complete,
            'on_track': on_track,
            'at_risk': at_risk,
            'not_started': not_started,
            'completion_pct': round((on_track / total * 100) if total > 0 else 0, 1)
        }
        
        # Get current quarter
        current_month = datetime.now().month
        current_quarter = f"Q{(current_month - 1) // 3 + 1}"
        current_year = datetime.now().year
        
        conn.close()
        
        can_edit = can_edit_division(user, division_id)
        
        return render_template('rocks.html',
                             user=user,
                             division=division,
                             rocks=rocks,
                             summary=summary,
                             current_quarter=current_quarter,
                             current_year=current_year,
                             can_edit=can_edit)
    
    @app.route('/division/<int:division_id>/rocks/add', methods=['GET', 'POST'])
    @login_required
    @division_edit_required('division_id')
    def add_rock(division_id):
        """Add a new rock"""
        user = session.get('user')
        
        if request.method == 'POST':
            description = request.form.get('description')
            owner = request.form.get('owner')
            due_date = request.form.get('due_date')
            quarter = request.form.get('quarter')
            year = request.form.get('year', datetime.now().year)
            priority = request.form.get('priority', 1)
            
            if not description or not owner:
                flash('Description and owner are required', 'danger')
                return redirect(url_for('add_rock', division_id=division_id))
            
            conn = get_db()
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO rocks (
                    organization_id, division_id, description, owner, 
                    due_date, quarter, year, priority, status, progress,
                    created_by, is_active
                )
                VALUES (
                    (SELECT organization_id FROM divisions WHERE id = ?),
                    ?, ?, ?, ?, ?, ?, ?, 'NOT STARTED', 0, ?, 1
                )
            """, (division_id, division_id, description, owner, due_date, 
                  quarter, year, priority, user['id']))
            
            rock_id = cursor.lastrowid
            
            log_action(
                user['id'], 'rocks', rock_id, 'CREATE',
                changes={'description': description, 'owner': owner, 'quarter': quarter},
                organization_id=1,
                division_id=division_id,
                ip_address=request.remote_addr
            )
            
            conn.commit()
            conn.close()
            
            flash(f'Rock added successfully', 'success')
            return redirect(url_for('division_rocks', division_id=division_id))
        
        # GET request - show form
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT d.*, o.name as org_name
            FROM divisions d
            JOIN organizations o ON d.organization_id = o.id
            WHERE d.id = ?
        """, (division_id,))
        division = dict(cursor.fetchone())
        conn.close()
        
        # Calculate current quarter
        current_month = datetime.now().month
        current_quarter = f"Q{(current_month - 1) // 3 + 1}"
        current_year = datetime.now().year
        
        return render_template('add_rock.html',
                             user=user,
                             division=division,
                             current_quarter=current_quarter,
                             current_year=current_year)
    
    @app.route('/api/division/<int:division_id>/rocks/<int:rock_id>', methods=['PUT'])
    @login_required
    @division_edit_required('division_id')
    def update_rock(division_id, rock_id):
        """Update a rock via API"""
        user = session.get('user')
        data = request.get_json()
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Build update query dynamically
        updates = []
        params = []
        
        allowed_fields = ['description', 'owner', 'status', 'due_date', 'progress', 'quarter', 'year', 'priority']
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(data[field])
        
        if not updates:
            return jsonify({'success': False, 'error': 'No valid fields to update'}), 400
        
        updates.append("updated_by = ?")
        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(user['id'])
        params.extend([rock_id, division_id])
        
        cursor.execute(f"""
            UPDATE rocks
            SET {', '.join(updates)}
            WHERE id = ? AND division_id = ?
        """, params)
        
        log_action(
            user['id'], 'rocks', rock_id, 'UPDATE',
            changes=data,
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Rock updated successfully'})
    
    @app.route('/api/division/<int:division_id>/rocks')
    @login_required
    @division_access_required('division_id')
    def api_rocks(division_id):
        """Get rocks as JSON"""
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                id, description as rock, owner, status, due_date,
                progress, quarter, year, priority, updated_at, updated_by
            FROM rocks
            WHERE division_id = ? AND is_active = 1
            ORDER BY year DESC, quarter DESC, priority
        """, (division_id,))
        
        rocks = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return jsonify(rocks)
