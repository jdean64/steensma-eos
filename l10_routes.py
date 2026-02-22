"""
EOS Platform - L10 Meetings Routes
Level 10 Meetings - fully interactive with inline editing and auto-save
Uses db_utils for retry-on-lock and context-managed connections
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, division_access_required, division_edit_required, log_action, can_edit_division
from db_utils import get_db_connection, execute_with_retry, retry_on_lock, log_to_audit
import sqlite3
import json
import time
from datetime import datetime, timedelta


def register_l10_routes(app):
    """Register L10 meeting routes"""

    # =========================================================
    # PAGE ROUTES (read-only, use context manager)
    # =========================================================

    @app.route('/division/<int:division_id>/l10')
    @login_required
    @division_access_required('division_id')
    def l10_meetings(division_id):
        """View all L10 meetings for a division"""
        user = session.get('user')
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT d.*, o.name as org_name
                FROM divisions d
                JOIN organizations o ON d.organization_id = o.id
                WHERE d.id = ?
            """, (division_id,))
            division = dict(cursor.fetchone())

            cursor.execute("""
                SELECT l.*, u.full_name as facilitator_name
                FROM l10_meetings l
                LEFT JOIN users u ON l.facilitator_user_id = u.id
                WHERE l.division_id = ? AND l.status IN ('SCHEDULED', 'IN_PROGRESS')
                ORDER BY l.meeting_date ASC, l.meeting_time ASC
                LIMIT 10
            """, (division_id,))
            upcoming_meetings = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT l.*, u.full_name as facilitator_name
                FROM l10_meetings l
                LEFT JOIN users u ON l.facilitator_user_id = u.id
                WHERE l.division_id = ? AND l.status = 'COMPLETED'
                ORDER BY l.meeting_date DESC, l.completed_at DESC
                LIMIT 20
            """, (division_id,))
            past_meetings = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT
                    COUNT(*) as total_meetings,
                    AVG(CAST(actual_duration_minutes AS FLOAT)) as avg_duration,
                    COUNT(CASE WHEN completed_at IS NOT NULL THEN 1 END) as completed_count
                FROM l10_meetings WHERE division_id = ?
            """, (division_id,))
            stats = dict(cursor.fetchone())

        can_edit = can_edit_division(user, division_id)
        return render_template('l10_meetings.html',
                               user=user, division=division,
                               upcoming_meetings=upcoming_meetings,
                               past_meetings=past_meetings,
                               stats=stats, can_edit=can_edit)

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
            duration_minutes = request.form.get('duration_minutes', 60)
            facilitator_user_id = request.form.get('facilitator_user_id')

            if not meeting_date:
                flash('Meeting date is required', 'danger')
                return redirect(url_for('add_l10_meeting', division_id=division_id))

            with get_db_connection() as conn:
                cursor = conn.cursor()
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

                standard_sections = [
                    ('Segue', 1, 5),
                    ('Headlines', 2, 5),
                    ('Scorecard Review', 3, 5),
                    ('Rock Review', 4, 5),
                    ('To-Do List Review', 5, 5),
                    ('IDS', 6, 30),
                    ('Conclude', 7, 5),
                ]
                for section_name, order, minutes in standard_sections:
                    cursor.execute("""
                        INSERT INTO l10_sections (
                            l10_meeting_id, section_name, section_order,
                            allocated_minutes, status
                        ) VALUES (?, ?, ?, ?, 'PENDING')
                    """, (meeting_id, section_name, order, minutes))

                conn.commit()

            # Log AFTER connection is closed (log_action opens its own connection)
            try:
                log_action(user['id'], 'l10_meetings', meeting_id, 'CREATE',
                           changes={'meeting_date': meeting_date, 'meeting_time': meeting_time},
                           organization_id=org_id, division_id=division_id,
                           ip_address=request.remote_addr)
            except Exception:
                pass  # Don't fail the request over audit logging

            flash(f'L10 meeting scheduled for {meeting_date}', 'success')
            return redirect(url_for('l10_meetings', division_id=division_id))

        # GET - show form
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT d.*, o.name as org_name
                FROM divisions d JOIN organizations o ON d.organization_id = o.id
                WHERE d.id = ?
            """, (division_id,))
            division = dict(cursor.fetchone())

            cursor.execute("""
                SELECT DISTINCT u.id, u.full_name, u.username
                FROM users u JOIN user_roles ur ON u.id = ur.user_id
                WHERE (ur.division_id = ? OR ur.division_id IS NULL) AND u.is_active = 1
                ORDER BY u.full_name
            """, (division_id,))
            users = [dict(row) for row in cursor.fetchall()]

        suggested_date = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        return render_template('add_l10_meeting.html',
                               user=user, division=division,
                               users=users, suggested_date=suggested_date)

    @app.route('/division/<int:division_id>/l10/<int:meeting_id>')
    @login_required
    @division_access_required('division_id')
    def view_l10_meeting(division_id, meeting_id):
        """View / conduct an L10 meeting - fully interactive"""
        user = session.get('user')
        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                SELECT l.*, d.display_name as division_name, u.full_name as facilitator_name
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

            cursor.execute("""
                SELECT * FROM l10_sections
                WHERE l10_meeting_id = ? ORDER BY section_order
            """, (meeting_id,))
            sections = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT r.*, u.full_name as owner_full_name
                FROM rocks r
                LEFT JOIN users u ON r.owner_user_id = u.id
                WHERE r.division_id = ? AND r.is_active = 1
                ORDER BY r.quarter DESC, r.priority
            """, (division_id,))
            rocks = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT i.*, u.full_name as owner_full_name
                FROM issues i
                LEFT JOIN users u ON i.owner_user_id = u.id
                WHERE i.division_id = ? AND i.is_active = 1 AND i.status != 'RESOLVED'
                ORDER BY
                    CASE i.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                    i.date_added DESC
            """, (division_id,))
            issues = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT t.*, u.full_name as owner_full_name
                FROM todos t
                LEFT JOIN users u ON t.owner_user_id = u.id
                WHERE t.division_id = ? AND t.is_active = 1 AND t.is_completed = 0
                ORDER BY
                    CASE t.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END,
                    t.due_date ASC
            """, (division_id,))
            todos = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT DISTINCT u.id, u.full_name, u.email
                FROM users u JOIN user_roles ur ON u.id = ur.user_id
                WHERE (ur.division_id = ? OR ur.division_id IS NULL) AND u.is_active = 1
                ORDER BY u.full_name
            """, (division_id,))
            users = [dict(row) for row in cursor.fetchall()]

        can_edit = can_edit_division(user, division_id)
        return render_template('view_l10_meeting.html',
                               user=user, meeting=meeting, sections=sections,
                               rocks=rocks, issues=issues, todos=todos,
                               users=users, division_id=division_id,
                               can_edit=can_edit)

    # =========================================================
    # MEETING LIFECYCLE (commit BEFORE log_action)
    # =========================================================

    @app.route('/division/<int:division_id>/l10/<int:meeting_id>/start', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def start_l10_meeting(division_id, meeting_id):
        user = session.get('user')
        # Use execute_with_retry for the write operation
        execute_with_retry("""
            UPDATE l10_meetings
            SET status = 'IN_PROGRESS', started_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND division_id = ?
        """, (meeting_id, division_id))

        # Log AFTER the write is committed and connection closed
        try:
            log_to_audit(user['id'], 'l10_meetings', meeting_id, 'UPDATE',
                         changes={'status': 'IN_PROGRESS'},
                         organization_id=1, division_id=division_id,
                         ip_address=request.remote_addr)
        except Exception:
            pass

        flash('L10 meeting started', 'success')
        return redirect(url_for('view_l10_meeting', division_id=division_id, meeting_id=meeting_id))

    @app.route('/division/<int:division_id>/l10/<int:meeting_id>/complete', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def complete_l10_meeting(division_id, meeting_id):
        user = session.get('user')

        meeting = execute_with_retry(
            "SELECT started_at FROM l10_meetings WHERE id = ? AND division_id = ?",
            (meeting_id, division_id), fetch='one', commit=False)

        if meeting and meeting.get('started_at'):
            try:
                started = datetime.fromisoformat(meeting['started_at'])
                duration = int((datetime.now() - started).total_seconds() / 60)
            except Exception:
                duration = 60
        else:
            duration = 60

        rating = request.form.get('rating', '')

        execute_with_retry("""
            UPDATE l10_meetings
            SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP,
                actual_duration_minutes = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND division_id = ?
        """, (duration, meeting_id, division_id))

        execute_with_retry("""
            UPDATE l10_sections SET status = 'COMPLETE', completed_at = CURRENT_TIMESTAMP
            WHERE l10_meeting_id = ? AND status != 'COMPLETE'
        """, (meeting_id,))

        try:
            log_to_audit(user['id'], 'l10_meetings', meeting_id, 'UPDATE',
                         changes={'status': 'COMPLETED', 'duration_minutes': duration, 'rating': rating},
                         organization_id=1, division_id=division_id,
                         ip_address=request.remote_addr)
        except Exception:
            pass

        flash(f'L10 meeting completed! Duration: {duration} minutes', 'success')
        return redirect(url_for('l10_meetings', division_id=division_id))

    # =========================================================
    # AJAX API - AUTO-SAVE (all use execute_with_retry + try/except)
    # =========================================================

    @app.route('/api/l10/<int:meeting_id>/save-notes', methods=['POST'])
    @login_required
    def l10_save_notes(meeting_id):
        """Save meeting-level notes with retry on lock"""
        try:
            data = request.get_json()
            field = data.get('field', '')
            value = data.get('value', '')

            allowed_fields = ['segue_good_news', 'customer_employee_headlines',
                              'scorecard_review', 'rock_review']
            if field not in allowed_fields:
                return jsonify({'success': False, 'error': 'Invalid field'}), 400

            execute_with_retry(
                f"UPDATE l10_meetings SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (value, meeting_id))
            return jsonify({'success': True})
        except sqlite3.OperationalError as e:
            return jsonify({'success': False, 'error': 'Database busy, will retry', 'retry': True}), 503
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/l10/<int:meeting_id>/save-section', methods=['POST'])
    @login_required
    def l10_save_section(meeting_id):
        """Save section notes with retry"""
        try:
            data = request.get_json()
            section_id = data.get('section_id')
            notes = data.get('notes', '')
            status = data.get('status', 'ACTIVE')

            update_fields = ['notes = ?', 'status = ?']
            params = [notes, status]
            if status == 'COMPLETE':
                update_fields.append('completed_at = CURRENT_TIMESTAMP')
            elif status == 'ACTIVE':
                update_fields.append('started_at = CURRENT_TIMESTAMP')
            params.extend([section_id, meeting_id])

            execute_with_retry(
                f"UPDATE l10_sections SET {', '.join(update_fields)} WHERE id = ? AND l10_meeting_id = ?",
                tuple(params))
            return jsonify({'success': True})
        except sqlite3.OperationalError:
            return jsonify({'success': False, 'error': 'Database busy', 'retry': True}), 503
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/l10/rock/<int:rock_id>/update', methods=['POST'])
    @login_required
    def l10_update_rock(rock_id):
        """Inline update a rock with retry"""
        try:
            data = request.get_json()
            updates = []
            params = []
            for field in ['status', 'progress', 'description', 'owner']:
                if field in data:
                    updates.append(f'{field} = ?')
                    params.append(data[field])
            if not updates:
                return jsonify({'success': False, 'error': 'Nothing to update'}), 400

            updates.append('updated_at = CURRENT_TIMESTAMP')
            params.append(rock_id)
            execute_with_retry(
                f"UPDATE rocks SET {', '.join(updates)} WHERE id = ?",
                tuple(params))
            return jsonify({'success': True})
        except sqlite3.OperationalError:
            return jsonify({'success': False, 'error': 'Database busy', 'retry': True}), 503
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/l10/todo/<int:todo_id>/update', methods=['POST'])
    @login_required
    def l10_update_todo(todo_id):
        """Inline update a todo with retry"""
        try:
            data = request.get_json()

            if data.get('is_completed'):
                execute_with_retry("""
                    UPDATE todos SET is_completed = 1, status = 'COMPLETE',
                        completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (todo_id,))
            elif 'is_completed' in data and not data['is_completed']:
                execute_with_retry("""
                    UPDATE todos SET is_completed = 0, status = 'OPEN',
                        completed_at = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (todo_id,))

            for field in ['task', 'owner', 'due_date', 'status']:
                if field in data and field != 'is_completed':
                    execute_with_retry(
                        f"UPDATE todos SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (data[field], todo_id))

            return jsonify({'success': True})
        except sqlite3.OperationalError:
            return jsonify({'success': False, 'error': 'Database busy', 'retry': True}), 503
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/l10/todo/create', methods=['POST'])
    @login_required
    def l10_create_todo():
        """Create a new todo from L10 meeting with retry"""
        try:
            data = request.get_json()
            user = session.get('user')

            division_id = data.get('division_id')
            row = execute_with_retry(
                "SELECT organization_id FROM divisions WHERE id = ?",
                (division_id,), fetch='one', commit=False)
            org_id = row['organization_id'] if row else 1

            new_id = execute_with_retry("""
                INSERT INTO todos (organization_id, division_id, task, owner, due_date,
                                   status, source, source_l10_id, created_by, created_at, is_active, is_completed)
                VALUES (?, ?, ?, ?, ?, 'OPEN', 'L10', ?, ?, CURRENT_TIMESTAMP, 1, 0)
            """, (org_id, division_id, data.get('task', ''), data.get('owner', ''),
                  data.get('due_date', ''), data.get('meeting_id'), user['id']),
                fetch='lastrowid')

            return jsonify({'success': True, 'id': new_id})
        except sqlite3.OperationalError:
            return jsonify({'success': False, 'error': 'Database busy', 'retry': True}), 503
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/l10/issue/<int:issue_id>/update', methods=['POST'])
    @login_required
    def l10_update_issue(issue_id):
        """Inline update an issue with retry"""
        try:
            data = request.get_json()
            updates = []
            params = []
            for field in ['status', 'priority', 'ids_stage', 'discussion_notes', 'solution', 'owner']:
                if field in data:
                    updates.append(f'{field} = ?')
                    params.append(data[field])

            if data.get('status') == 'RESOLVED':
                updates.append('resolved_at = CURRENT_TIMESTAMP')

            if updates:
                updates.append('updated_at = CURRENT_TIMESTAMP')
                params.append(issue_id)
                execute_with_retry(
                    f"UPDATE issues SET {', '.join(updates)} WHERE id = ?",
                    tuple(params))

            return jsonify({'success': True})
        except sqlite3.OperationalError:
            return jsonify({'success': False, 'error': 'Database busy', 'retry': True}), 503
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/l10/issue/create', methods=['POST'])
    @login_required
    def l10_create_issue():
        """Create a new issue from L10 meeting with retry"""
        try:
            data = request.get_json()
            user = session.get('user')

            division_id = data.get('division_id')
            row = execute_with_retry(
                "SELECT organization_id FROM divisions WHERE id = ?",
                (division_id,), fetch='one', commit=False)
            org_id = row['organization_id'] if row else 1

            new_id = execute_with_retry("""
                INSERT INTO issues (organization_id, division_id, issue, priority, owner,
                                    status, category, ids_stage, added_from_l10_id,
                                    date_added, created_by, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, 'OPEN', ?, 'IDENTIFY', ?, date('now'), ?, CURRENT_TIMESTAMP, 1)
            """, (org_id, division_id, data.get('issue', ''), data.get('priority', 'MEDIUM'),
                  data.get('owner', ''), data.get('category', 'ADMINISTRATIVE'),
                  data.get('meeting_id'), user['id']),
                fetch='lastrowid')

            return jsonify({'success': True, 'id': new_id})
        except sqlite3.OperationalError:
            return jsonify({'success': False, 'error': 'Database busy', 'retry': True}), 503
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/l10/<int:meeting_id>/complete-email', methods=['POST'])
    @login_required
    def l10_complete_with_email(meeting_id):
        """Complete meeting and send email summary"""
        try:
            data = request.get_json()
            user = session.get('user')
            emails = data.get('emails', [])
            rating = data.get('rating', '')
            notes = data.get('notes', '')

            # Read meeting info
            meeting = execute_with_retry(
                "SELECT started_at, meeting_date, division_id FROM l10_meetings WHERE id = ?",
                (meeting_id,), fetch='one', commit=False)

            if not meeting:
                return jsonify({'success': False, 'error': 'Meeting not found'}), 404

            division_id = meeting['division_id']
            if meeting.get('started_at'):
                try:
                    started = datetime.fromisoformat(meeting['started_at'])
                    duration = int((datetime.now() - started).total_seconds() / 60)
                except Exception:
                    duration = 60
            else:
                duration = 60

            # Complete meeting
            execute_with_retry("""
                UPDATE l10_meetings SET status = 'COMPLETED', completed_at = CURRENT_TIMESTAMP,
                    actual_duration_minutes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (duration, meeting_id))

            execute_with_retry("""
                UPDATE l10_sections SET status = 'COMPLETE', completed_at = CURRENT_TIMESTAMP
                WHERE l10_meeting_id = ? AND status != 'COMPLETE'
            """, (meeting_id,))

            # Gather summary data (read-only)
            div_row = execute_with_retry(
                "SELECT display_name FROM divisions WHERE id = ?",
                (division_id,), fetch='one', commit=False)
            div_name = div_row['display_name'] if div_row else 'Division'

            m = execute_with_retry(
                "SELECT segue_good_news, customer_employee_headlines, scorecard_review, rock_review FROM l10_meetings WHERE id = ?",
                (meeting_id,), fetch='one', commit=False) or {}

            new_todos = execute_with_retry(
                "SELECT task, owner FROM todos WHERE source_l10_id = ? AND is_active = 1",
                (meeting_id,), fetch='all', commit=False) or []

            # Build email
            meeting_date = meeting['meeting_date']
            subject = f"L10 Meeting Summary - {div_name} - {meeting_date}"

            html_body = f"""
            <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif; max-width: 650px; margin: 0 auto;">
                <div style="background: #1a1a1a; color: white; padding: 24px 32px; border-radius: 8px 8px 0 0;">
                    <h1 style="margin: 0; font-size: 22px;">L10 Meeting Summary</h1>
                    <p style="margin: 8px 0 0; color: #b0b0b0;">{div_name} &bull; {meeting_date} &bull; {duration} min</p>
                </div>
                <div style="background: #ffffff; padding: 24px 32px; border: 1px solid #e0e0e0;">
                    <p><strong>Meeting Rating:</strong> {rating}/10</p>
            """

            if m.get('segue_good_news'):
                html_body += f"<h3 style='margin-top:20px;'>Segue</h3><p>{m['segue_good_news']}</p>"
            if m.get('customer_employee_headlines'):
                html_body += f"<h3 style='margin-top:20px;'>Headlines</h3><p>{m['customer_employee_headlines']}</p>"
            if m.get('scorecard_review'):
                html_body += f"<h3 style='margin-top:20px;'>Scorecard Review</h3><p>{m['scorecard_review']}</p>"
            if m.get('rock_review'):
                html_body += f"<h3 style='margin-top:20px;'>Rock Review</h3><p>{m['rock_review']}</p>"

            if new_todos:
                html_body += "<h3 style='margin-top:20px;'>New To-Dos</h3><ul>"
                for t in new_todos:
                    html_body += f"<li><strong>{t['owner']}:</strong> {t['task']}</li>"
                html_body += "</ul>"

            if notes:
                html_body += f"<h3 style='margin-top:20px;'>Conclude Notes</h3><p>{notes}</p>"

            html_body += """
                </div>
                <div style="background: #f5f5f5; padding: 16px 32px; border-radius: 0 0 8px 8px; border: 1px solid #e0e0e0; border-top: none; font-size: 12px; color: #888;">
                    Sent from EOS Platform &bull; eos.coresteensma.com
                </div>
            </div>
            """

            # Send emails
            email_results = []
            if emails:
                try:
                    import boto3
                    ses = boto3.client('ses', region_name='us-east-2')
                    for email_addr in emails:
                        email_addr = email_addr.strip()
                        if not email_addr:
                            continue
                        try:
                            ses.send_email(
                                Source='eos@coresteensma.com',
                                Destination={'ToAddresses': [email_addr]},
                                Message={
                                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                                    'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
                                }
                            )
                            email_results.append({'email': email_addr, 'status': 'sent'})
                        except Exception as e:
                            email_results.append({'email': email_addr, 'status': 'failed', 'error': str(e)})
                except ImportError:
                    email_results = [{'email': e, 'status': 'skipped', 'error': 'Email service not configured'} for e in emails]

            return jsonify({
                'success': True,
                'duration': duration,
                'emails_sent': email_results
            })
        except sqlite3.OperationalError:
            return jsonify({'success': False, 'error': 'Database busy', 'retry': True}), 503
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
