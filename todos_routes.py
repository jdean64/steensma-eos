"""
EOS Platform - To-Dos Routes
Action items with owners and due dates, with email notification support
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

        # Get users for owner dropdown and email notifications
        cursor.execute("""
            SELECT DISTINCT u.id, u.full_name, u.email
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE ur.division_id = ? AND u.is_active = 1
            ORDER BY u.full_name
        """, (division_id,))
        users = [dict(row) for row in cursor.fetchall()]

        # Check email configuration status
        from email_service import is_email_configured
        email_configured = is_email_configured()

        conn.close()

        can_edit = can_edit_division(user, division_id)

        return render_template('todos.html',
                             user=user,
                             division=division,
                             todos=todos,
                             summary=summary,
                             users=users,
                             email_configured=email_configured,
                             can_edit=can_edit,
                             now_str=datetime.now().strftime('%Y-%m-%d'))

    @app.route('/division/<int:division_id>/todos/add', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def add_todo(division_id):
        """Add a new to-do"""
        user = session.get('user')

        task = request.form.get('task', '').strip()
        owner = request.form.get('owner', '').strip()
        due_date = request.form.get('due_date', '').strip()
        priority = request.form.get('priority', 'MEDIUM')

        if not task:
            flash('Task description is required', 'danger')
            return redirect(url_for('division_todos', division_id=division_id))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT organization_id FROM divisions WHERE id = ?", (division_id,))
        org_id = cursor.fetchone()['organization_id']

        # Look up owner user id if we can match by name
        owner_user_id = None
        if owner:
            cursor.execute("""
                SELECT u.id FROM users u
                JOIN user_roles ur ON u.id = ur.user_id
                WHERE ur.division_id = ? AND u.full_name = ? AND u.is_active = 1
            """, (division_id, owner))
            owner_row = cursor.fetchone()
            if owner_row:
                owner_user_id = owner_row['id']

        cursor.execute("""
            INSERT INTO todos (
                organization_id, division_id, task, owner, owner_user_id,
                due_date, status, priority, source, created_by,
                is_active, is_completed
            )
            VALUES (?, ?, ?, ?, ?, ?, 'OPEN', ?, 'MANUAL', ?, 1, 0)
        """, (org_id, division_id, task, owner or 'Unassigned', owner_user_id,
              due_date or None, priority, user['id']))

        todo_id = cursor.lastrowid

        log_action(
            user['id'], 'todos', todo_id, 'CREATE',
            changes={'task': task, 'owner': owner, 'priority': priority},
            organization_id=org_id,
            division_id=division_id,
            ip_address=request.remote_addr
        )

        conn.commit()
        conn.close()

        flash(f'To-Do added: {task[:50]}', 'success')
        return redirect(url_for('division_todos', division_id=division_id))

    @app.route('/division/<int:division_id>/todos/<int:todo_id>/complete', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def complete_todo(division_id, todo_id):
        """Mark a to-do as complete"""
        user = session.get('user')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE todos
            SET status = 'COMPLETE', is_completed = 1,
                completed_at = CURRENT_TIMESTAMP, completed_by = ?,
                updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND division_id = ?
        """, (user['id'], user['id'], todo_id, division_id))

        conn.commit()
        conn.close()

        flash('To-Do marked as complete', 'success')
        return redirect(url_for('division_todos', division_id=division_id))

    @app.route('/division/<int:division_id>/todos/<int:todo_id>/reopen', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def reopen_todo(division_id, todo_id):
        """Reopen a completed to-do"""
        user = session.get('user')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE todos
            SET status = 'OPEN', is_completed = 0,
                completed_at = NULL, completed_by = NULL,
                updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND division_id = ?
        """, (user['id'], todo_id, division_id))

        conn.commit()
        conn.close()

        flash('To-Do reopened', 'success')
        return redirect(url_for('division_todos', division_id=division_id))

    @app.route('/division/<int:division_id>/todos/<int:todo_id>/delete', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def delete_todo(division_id, todo_id):
        """Soft-delete a to-do"""
        user = session.get('user')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE todos
            SET is_active = 0, updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND division_id = ?
        """, (user['id'], todo_id, division_id))

        conn.commit()
        conn.close()

        flash('To-Do removed', 'success')
        return redirect(url_for('division_todos', division_id=division_id))

    @app.route('/division/<int:division_id>/todos/notify', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def send_todo_notifications(division_id):
        """Send email notifications for assigned tasks to owners and their leads"""
        user = session.get('user')

        from email_service import send_task_notification, is_email_configured

        if not is_email_configured():
            flash('Email is not configured. Set EOS_SMTP_HOST, EOS_SMTP_USER, EOS_SMTP_PASS environment variables.', 'danger')
            return redirect(url_for('division_todos', division_id=division_id))

        conn = get_db()
        cursor = conn.cursor()

        # Get division name
        cursor.execute("SELECT display_name FROM divisions WHERE id = ?", (division_id,))
        division_name = cursor.fetchone()['display_name']

        # Get all open todos grouped by owner
        cursor.execute("""
            SELECT t.id, t.task, t.owner, t.due_date, t.priority, t.source,
                   t.owner_user_id, u.email as owner_email, u.full_name as owner_full_name
            FROM todos t
            LEFT JOIN users u ON t.owner_user_id = u.id
            WHERE t.division_id = ? AND t.is_active = 1
                  AND (t.is_completed = 0 OR t.is_completed IS NULL)
            ORDER BY t.owner, t.priority
        """, (division_id,))

        todos = [dict(row) for row in cursor.fetchall()]

        # Group by owner
        owners = {}
        for t in todos:
            owner_key = t.get('owner_user_id') or t.get('owner', 'Unassigned')
            if owner_key not in owners:
                owners[owner_key] = {
                    'email': t.get('owner_email'),
                    'name': t.get('owner_full_name') or t.get('owner', 'Unassigned'),
                    'user_id': t.get('owner_user_id'),
                    'tasks': []
                }
            owners[owner_key]['tasks'].append(t)

        # Find leads/managers from accountability chart
        cursor.execute("""
            SELECT ac.user_id, ac.seat_name, ac.reports_to_seat_id,
                   parent.user_id as lead_user_id
            FROM accountability_chart ac
            LEFT JOIN accountability_chart parent ON ac.reports_to_seat_id = parent.id
            WHERE ac.division_id = ? AND ac.user_id IS NOT NULL
        """, (division_id,))
        lead_map = {}
        for row in cursor.fetchall():
            row = dict(row)
            if row.get('user_id') and row.get('lead_user_id'):
                lead_map[row['user_id']] = row['lead_user_id']

        # Get lead email addresses
        lead_emails = {}
        lead_user_ids = set(lead_map.values())
        if lead_user_ids:
            placeholders = ','.join('?' * len(lead_user_ids))
            cursor.execute(f"""
                SELECT id, email, full_name FROM users
                WHERE id IN ({placeholders}) AND is_active = 1
            """, list(lead_user_ids))
            for row in cursor.fetchall():
                row = dict(row)
                lead_emails[row['id']] = {'email': row['email'], 'name': row['full_name']}

        conn.close()

        sent_count = 0
        errors = []

        for owner_key, owner_data in owners.items():
            # Send to owner
            if owner_data['email']:
                success, err = send_task_notification(
                    owner_data['email'],
                    owner_data['name'],
                    owner_data['tasks'],
                    division_name
                )
                if success:
                    sent_count += 1
                elif err:
                    errors.append(f"{owner_data['name']}: {err}")

            # Send to their lead
            if owner_data['user_id'] and owner_data['user_id'] in lead_map:
                lead_id = lead_map[owner_data['user_id']]
                if lead_id in lead_emails:
                    lead = lead_emails[lead_id]
                    success, err = send_task_notification(
                        lead['email'],
                        lead['name'],
                        owner_data['tasks'],
                        f"{division_name} - {owner_data['name']}'s Tasks"
                    )
                    if success:
                        sent_count += 1
                    elif err:
                        errors.append(f"Lead {lead['name']}: {err}")

        if sent_count > 0:
            flash(f'Sent {sent_count} notification email(s) successfully', 'success')
        if errors:
            flash(f'Some emails failed: {"; ".join(errors[:3])}', 'danger')
        if sent_count == 0 and not errors:
            flash('No emails to send - no owners have email addresses configured', 'danger')

        return redirect(url_for('division_todos', division_id=division_id))

    @app.route('/division/<int:division_id>/todos/notify-preview')
    @login_required
    @division_access_required('division_id')
    def preview_notifications(division_id):
        """Preview who would receive notifications"""
        user = session.get('user')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT display_name FROM divisions WHERE id = ?", (division_id,))
        division_name = cursor.fetchone()['display_name']

        cursor.execute("""
            SELECT t.owner, t.owner_user_id, u.email as owner_email,
                   u.full_name as owner_full_name, COUNT(*) as task_count
            FROM todos t
            LEFT JOIN users u ON t.owner_user_id = u.id
            WHERE t.division_id = ? AND t.is_active = 1
                  AND (t.is_completed = 0 OR t.is_completed IS NULL)
            GROUP BY t.owner_user_id, t.owner
            ORDER BY t.owner
        """, (division_id,))

        preview = []
        for row in cursor.fetchall():
            row = dict(row)
            preview.append({
                'name': row.get('owner_full_name') or row.get('owner', 'Unassigned'),
                'email': row.get('owner_email', 'No email'),
                'task_count': row['task_count'],
                'can_send': bool(row.get('owner_email'))
            })

        conn.close()

        from email_service import is_email_configured
        return jsonify({
            'email_configured': is_email_configured(),
            'division': division_name,
            'recipients': preview
        })
