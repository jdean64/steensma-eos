"""
EOS Platform - L10 Meetings Routes
Level 10 Meetings with time-stamped completion tracking
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, division_access_required, division_edit_required, log_action, can_edit_division
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timedelta

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def get_db():
    """Get database connection with timeout for concurrent access"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA busy_timeout=30000')
    return conn

def register_l10_routes(app):
    """Register L10 meeting routes"""
    
    @app.route('/division/<int:division_id>/l10')
    @login_required
    @division_access_required('division_id')
    def l10_meetings(division_id):
        """View all L10 meetings for a division"""
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
        
        # Get upcoming meetings
        cursor.execute("""
            SELECT 
                l.*,
                u.full_name as facilitator_name
            FROM l10_meetings l
            LEFT JOIN users u ON l.facilitator_user_id = u.id
            WHERE l.division_id = ? 
                AND l.status IN ('SCHEDULED', 'IN_PROGRESS')
            ORDER BY l.meeting_date ASC, l.meeting_time ASC
            LIMIT 10
        """, (division_id,))
        upcoming_meetings = [dict(row) for row in cursor.fetchall()]
        
        # Get past meetings (last 30 days)
        cursor.execute("""
            SELECT 
                l.*,
                u.full_name as facilitator_name
            FROM l10_meetings l
            LEFT JOIN users u ON l.facilitator_user_id = u.id
            WHERE l.division_id = ? 
                AND l.status = 'COMPLETED'
            ORDER BY l.meeting_date DESC, l.completed_at DESC
            LIMIT 20
        """, (division_id,))
        past_meetings = [dict(row) for row in cursor.fetchall()]
        
        # Get statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_meetings,
                AVG(CAST(actual_duration_minutes AS FLOAT)) as avg_duration,
                COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) as completed_count
            FROM l10_meetings
            WHERE division_id = ?
        """, (division_id,))
        stats = dict(cursor.fetchone())
        
        conn.close()
        
        can_edit = can_edit_division(user, division_id)
        
        return render_template('l10_meetings.html',
                             user=user,
                             division=division,
                             upcoming_meetings=upcoming_meetings,
                             past_meetings=past_meetings,
                             stats=stats,
                             can_edit=can_edit)
    
    @app.route('/division/<int:division_id>/l10/add', methods=['GET', 'POST'])
    @login_required
    @division_edit_required('division_id')
    def add_l10_meeting(division_id):
        """Schedule a new L10 meeting"""
        user = session.get('user')
        
        if request.method == 'POST':
            meeting_date = request.form.get('meeting_date')
            meeting_time = request.form.get('meeting_time', '09:00')
            frequency = request.form.get('frequency', 'WEEKLY')
            duration_minutes = request.form.get('duration_minutes', 90)
            facilitator_user_id = request.form.get('facilitator_user_id')
            
            if not meeting_date:
                flash('Meeting date is required', 'danger')
                return redirect(url_for('add_l10_meeting', division_id=division_id))
            
            conn = get_db()
            cursor = conn.cursor()
            
            # Get organization_id for this division
            cursor.execute("SELECT organization_id FROM divisions WHERE id = ?", (division_id,))
            org_id = cursor.fetchone()['organization_id']
            
            cursor.execute("""
                INSERT INTO l10_meetings (
                    organization_id, division_id, meeting_date, meeting_time,
                    frequency, duration_minutes, status, facilitator_user_id,
                    created_by, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 'SCHEDULED', ?, ?, CURRENT_TIMESTAMP)
            """, (org_id, division_id, meeting_date, meeting_time, frequency,
                  duration_minutes, facilitator_user_id, user['id']))
            
            meeting_id = cursor.lastrowid
            
            # Create standard L10 sections
            standard_sections = [
                ('Segue', 1, 5),
                ('Scorecard Review', 2, 5),
                ('Rock Review', 3, 5),
                ('Customer/Employee Headlines', 4, 5),
                ('To-Do List Review', 5, 5),
                ('IDS', 6, 60),
                ('Conclude', 7, 5)
            ]
            
            for section_name, order, minutes in standard_sections:
                cursor.execute("""
                    INSERT INTO l10_sections (
                        l10_meeting_id, section_name, section_order,
                        allocated_minutes, status
                    )
                    VALUES (?, ?, ?, ?, 'PENDING')
                """, (meeting_id, section_name, order, minutes))
            
            log_action(
                user['id'], 'l10_meetings', meeting_id, 'CREATE',
                changes={'meeting_date': meeting_date, 'meeting_time': meeting_time},
                organization_id=org_id,
                division_id=division_id,
                ip_address=request.remote_addr
            )
            
            conn.commit()
            conn.close()
            
            flash(f'L10 meeting scheduled for {meeting_date}', 'success')
            return redirect(url_for('l10_meetings', division_id=division_id))
        
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
        
        # Get users for facilitator dropdown
        cursor.execute("""
            SELECT DISTINCT u.id, u.full_name, u.username
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE ur.division_id = ? AND u.is_active = 1
            ORDER BY u.full_name
        """, (division_id,))
        users = [dict(row) for row in cursor.fetchall()]
        
        # Suggest next meeting date (next week, same day)
        suggested_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        conn.close()
        
        return render_template('add_l10_meeting.html',
                             user=user,
                             division=division,
                             users=users,
                             suggested_date=suggested_date)
    
    @app.route('/division/<int:division_id>/l10/<int:meeting_id>')
    @login_required
    @division_access_required('division_id')
    def view_l10_meeting(division_id, meeting_id):
        """View/conduct an L10 meeting"""
        user = session.get('user')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get meeting details
        cursor.execute("""
            SELECT 
                l.*,
                d.display_name as division_name,
                u.full_name as facilitator_name
            FROM l10_meetings l
            JOIN divisions d ON l.division_id = d.id
            LEFT JOIN users u ON l.facilitator_user_id = u.id
            WHERE l.id = ? AND l.division_id = ?
        """, (meeting_id, division_id))
        
        meeting = cursor.fetchone()
        if not meeting:
            flash('Meeting not found', 'danger')
            return redirect(url_for('l10_meetings', division_id=division_id))
        
        meeting = dict(meeting)
        
        # Get sections
        cursor.execute("""
            SELECT *
            FROM l10_sections
            WHERE l10_meeting_id = ?
            ORDER BY section_order
        """, (meeting_id,))
        sections = [dict(row) for row in cursor.fetchall()]
        
        # Get recent rocks for Rock Review section
        cursor.execute("""
            SELECT *
            FROM rocks
            WHERE division_id = ? AND is_active = 1
            ORDER BY quarter DESC, priority
            LIMIT 5
        """, (division_id,))
        rocks = [dict(row) for row in cursor.fetchall()]
        
        # Get open issues for IDS section
        cursor.execute("""
            SELECT i.*, u.full_name as owner_full_name
            FROM issues i
            LEFT JOIN users u ON i.owner_user_id = u.id
            WHERE i.division_id = ? AND i.is_active = 1 AND i.status != 'RESOLVED'
            ORDER BY 
                CASE i.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                i.date_added DESC
            LIMIT 10
        """, (division_id,))
        issues = [dict(row) for row in cursor.fetchall()]
        
        # Get todos for To-Do Review section
        cursor.execute("""
            SELECT t.*, u.full_name as owner_full_name
            FROM todos t
            LEFT JOIN users u ON t.owner_user_id = u.id
            WHERE t.division_id = ? AND t.is_active = 1 AND t.is_completed = 0
            ORDER BY 
                CASE t.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                t.due_date ASC
            LIMIT 10
        """, (division_id,))
        todos = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        can_edit = can_edit_division(user, division_id)
        
        return render_template('view_l10_meeting.html',
                             user=user,
                             meeting=meeting,
                             sections=sections,
                             rocks=rocks,
                             issues=issues,
                             todos=todos,
                             division_id=division_id,
                             can_edit=can_edit)
    
    @app.route('/division/<int:division_id>/l10/<int:meeting_id>/start', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def start_l10_meeting(division_id, meeting_id):
        """Start an L10 meeting"""
        user = session.get('user')
        
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE l10_meetings
            SET status = 'IN_PROGRESS',
                started_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND division_id = ?
        """, (meeting_id, division_id))
        
        log_action(
            user['id'], 'l10_meetings', meeting_id, 'UPDATE',
            changes={'status': 'IN_PROGRESS'},
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )
        
        conn.commit()
        conn.close()
        
        flash('L10 meeting started', 'success')
        return redirect(url_for('view_l10_meeting', division_id=division_id, meeting_id=meeting_id))
    
    @app.route('/division/<int:division_id>/l10/<int:meeting_id>/complete', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def complete_l10_meeting(division_id, meeting_id):
        """Complete an L10 meeting with timestamp"""
        user = session.get('user')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Calculate actual duration
        cursor.execute("""
            SELECT started_at
            FROM l10_meetings
            WHERE id = ? AND division_id = ?
        """, (meeting_id, division_id))
        
        meeting = cursor.fetchone()
        if meeting and meeting['started_at']:
            started = datetime.fromisoformat(meeting['started_at'])
            ended = datetime.now()
            duration = int((ended - started).total_seconds() / 60)
        else:
            duration = 90  # default
        
        cursor.execute("""
            UPDATE l10_meetings
            SET status = 'COMPLETED',
                completed_at = CURRENT_TIMESTAMP,
                actual_duration_minutes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND division_id = ?
        """, (duration, meeting_id, division_id))
        
        # Mark all sections as complete
        cursor.execute("""
            UPDATE l10_sections
            SET status = 'COMPLETE',
                completed_at = CURRENT_TIMESTAMP
            WHERE l10_meeting_id = ? AND status != 'COMPLETE'
        """, (meeting_id,))
        
        log_action(
            user['id'], 'l10_meetings', meeting_id, 'UPDATE',
            changes={'status': 'COMPLETED', 'duration_minutes': duration},
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )
        
        conn.commit()
        conn.close()
        
        flash(f'L10 meeting completed! Duration: {duration} minutes', 'success')
        return redirect(url_for('l10_meetings', division_id=division_id))
    
    @app.route('/division/<int:division_id>/l10/<int:meeting_id>/section/<int:section_id>/update', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def update_l10_section(division_id, meeting_id, section_id):
        """Update L10 section status and notes"""
        notes = request.form.get('notes', '')
        status = request.form.get('status', 'ACTIVE')
        
        conn = get_db()
        cursor = conn.cursor()
        
        update_fields = ['notes = ?', 'status = ?']
        params = [notes, status]
        
        if status == 'COMPLETE':
            update_fields.append('completed_at = CURRENT_TIMESTAMP')
        elif status == 'ACTIVE':
            update_fields.append('started_at = CURRENT_TIMESTAMP')
        
        params.extend([section_id, meeting_id])
        
        cursor.execute(f"""
            UPDATE l10_sections
            SET {', '.join(update_fields)}
            WHERE id = ? AND l10_meeting_id = ?
        """, params)
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Section updated'})
