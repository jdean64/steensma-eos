"""
EOS Platform - Issues Routes
IDS (Identify, Discuss, Solve) workflow with categories
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, division_access_required, division_edit_required, can_edit_division
from db_utils import get_db_connection, retry_on_lock, log_to_audit
import sqlite3
from pathlib import Path
from datetime import datetime

def register_issues_routes(app):
    """Register issues-related routes"""
    
    @app.route('/division/<int:division_id>/issues')
    @login_required
    @division_access_required('division_id')
    @retry_on_lock(max_retries=3)
    def division_issues(division_id):
        """View all issues for a division"""
        user = session.get('user')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get division info
            cursor.execute("""
                SELECT d.*, o.name as org_name
                FROM divisions d
                JOIN organizations o ON d.organization_id = o.id
                WHERE d.id = ?
            """, (division_id,))
            division = dict(cursor.fetchone())
            
            # Get all active issues
            cursor.execute("""
                SELECT 
                    i.*,
                    u.full_name as owner_full_name
                FROM issues i
                LEFT JOIN users u ON i.owner_user_id = u.id
                WHERE i.division_id = ? AND i.is_active = 1
                ORDER BY 
                    CASE i.priority
                        WHEN 'HIGH' THEN 1
                        WHEN 'MEDIUM' THEN 2
                        WHEN 'LOW' THEN 3
                        ELSE 4
                    END,
                    CASE i.status
                        WHEN 'OPEN' THEN 1
                        WHEN 'IN PROGRESS' THEN 2
                        WHEN 'RESOLVED' THEN 3
                        ELSE 4
                    END,
                    i.date_added DESC
            """, (division_id,))
            
            issues = [dict(row) for row in cursor.fetchall()]
            
            # Get summary by category
            cursor.execute("""
                SELECT 
                    category,
                    COUNT(*) as count
                FROM issues
                WHERE division_id = ? AND is_active = 1 AND status != 'RESOLVED'
                GROUP BY category
            """, (division_id,))
            category_summary = {row['category']: row['count'] for row in cursor.fetchall()}
            
            # Get all divisions for move functionality
            cursor.execute("""
                SELECT id, display_name
                FROM divisions
                WHERE organization_id = 1 AND is_active = 1
                ORDER BY display_name
            """)
            all_divisions = [dict(row) for row in cursor.fetchall()]
        
            can_edit = can_edit_division(user, division_id)
            
            # Get division users for owner dropdown
            cursor.execute("""
                SELECT DISTINCT u.id, u.full_name
                FROM users u
                JOIN user_roles ur ON u.id = ur.user_id
                WHERE ur.division_id = ? AND u.is_active = 1
                ORDER BY u.full_name
            """, (division_id,))
            users = [dict(row) for row in cursor.fetchall()]

            # Get current date for rock quarter calculation
            from datetime import datetime
            now = datetime.now()
            
            return render_template('issues_new.html',
                                 user=user,
                                 division=division,
                                 issues=issues,
                                 category_summary=category_summary,
                                 can_edit=can_edit,
                                 all_divisions=all_divisions,
                                 users=users,
                             now=now)
    
    @app.route('/division/<int:division_id>/issues/add', methods=['GET', 'POST'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def add_issue(division_id):
        """Add a new issue"""
        user = session.get('user')
        
        if request.method == 'POST':
            issue = request.form.get('issue')
            category = request.form.get('category')
            priority = request.form.get('priority', 'MEDIUM')
            owner_name = request.form.get('owner_name')
            discussion_notes = request.form.get('discussion_notes', '')
            
            if not issue or not category:
                flash('Issue description and category are required', 'danger')
                return redirect(url_for('add_issue', division_id=division_id))
            
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO issues (
                        organization_id, division_id, issue, category, priority,
                        owner, owner_name, date_added, status, ids_stage, discussion_notes,
                        created_by, updated_by
                    )
                    VALUES (
                        (SELECT organization_id FROM divisions WHERE id = ?),
                        ?, ?, ?, ?, ?, ?, ?, 'OPEN', 'IDENTIFY', ?, ?, ?
                    )
                """, (division_id, division_id, issue, category, priority, 
                      owner_name or 'Unassigned', owner_name,
                      datetime.now().strftime('%Y-%m-%d'),
                      discussion_notes, user['id'], user['id']))
                
                issue_id = cursor.lastrowid
                conn.commit()
            
            # Log the action in separate transaction
            log_to_audit(
                user['id'], 'issues', issue_id, 'CREATE',
                changes={'issue': issue, 'category': category, 'priority': priority},
                organization_id=1,
                division_id=division_id,
                ip_address=request.remote_addr
            )
            
            flash(f'Issue added successfully: {issue[:50]}...', 'success')
            return redirect(url_for('division_issues', division_id=division_id))
        
        # GET request - show form
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT d.*, o.name as org_name
                FROM divisions d
                JOIN organizations o ON d.organization_id = o.id
                WHERE d.id = ?
            """, (division_id,))
            division = dict(cursor.fetchone())
        
            return render_template('add_issue.html',
                                 user=user,
                                 division=division)
    
    @app.route('/division/<int:division_id>/issues/<int:issue_id>/edit', methods=['GET', 'POST'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def edit_issue(division_id, issue_id):
        """Edit an existing issue"""
        user = session.get('user')
        
        if request.method == 'POST':
            issue_text = request.form.get('issue')
            category = request.form.get('category')
            priority = request.form.get('priority')
            status = request.form.get('status')
            owner_name = request.form.get('owner_name')
            discussion_notes = request.form.get('discussion_notes', '')
            ids_stage = request.form.get('ids_stage', 'IDENTIFY')
            solution = request.form.get('solution', '')
            
            # Use context manager to ensure connection is closed
            with get_db_connection() as conn:
                cursor = conn.cursor()
                
                # Get old values for audit
                cursor.execute("SELECT * FROM issues WHERE id = ?", (issue_id,))
                old_issue = dict(cursor.fetchone())
                
                # Update issue
                cursor.execute("""
                    UPDATE issues
                    SET issue = ?, category = ?, priority = ?, status = ?,
                        owner_name = ?, discussion_notes = ?, ids_stage = ?,
                        solution = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP,
                        resolved_at = CASE WHEN ? = 'RESOLVED' AND status != 'RESOLVED' 
                                          THEN CURRENT_TIMESTAMP ELSE resolved_at END,
                        resolved_by = CASE WHEN ? = 'RESOLVED' AND status != 'RESOLVED'
                                          THEN ? ELSE resolved_by END
                    WHERE id = ? AND division_id = ?
                """, (issue_text, category, priority, status, owner_name, 
                      discussion_notes, ids_stage, solution, user['id'],
                      status, status, user['id'], issue_id, division_id))
                
                # Log changes to history
                changes = {}
                if old_issue['issue'] != issue_text:
                    changes['issue'] = {'old': old_issue['issue'], 'new': issue_text}
                if old_issue['status'] != status:
                    changes['status'] = {'old': old_issue['status'], 'new': status}
                if old_issue['priority'] != priority:
                    changes['priority'] = {'old': old_issue['priority'], 'new': priority}
                
                if changes:
                    for field, change in changes.items():
                        cursor.execute("""
                            INSERT INTO issues_history (issue_id, field_changed, old_value, new_value, changed_by)
                            VALUES (?, ?, ?, ?, ?)
                        """, (issue_id, field, str(change['old']), str(change['new']), user['id']))
                
                conn.commit()
            
            # Log to audit in separate transaction with retry
            log_to_audit(
                user['id'], 'issues', issue_id, 'UPDATE',
                changes=changes,
                organization_id=1,
                division_id=division_id,
                ip_address=request.remote_addr
            )
            
            flash('Issue updated successfully', 'success')
            return redirect(url_for('division_issues', division_id=division_id))
        
        # GET request - show form
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT i.*, d.display_name as division_name
                FROM issues i
                JOIN divisions d ON i.division_id = d.id
                WHERE i.id = ? AND i.division_id = ?
            """, (issue_id, division_id))
            
            issue = cursor.fetchone()
            if not issue:
                flash('Issue not found', 'danger')
                return redirect(url_for('division_issues', division_id=division_id))
            
            issue = dict(issue)
            
            # Get issue history
            cursor.execute("""
                SELECT ih.*, u.full_name as changed_by_name
                FROM issues_history ih
                LEFT JOIN users u ON ih.changed_by = u.id
                WHERE ih.issue_id = ?
                ORDER BY ih.changed_at DESC
            """, (issue_id,))
            
            history = [dict(row) for row in cursor.fetchall()]
        
            return render_template('edit_issue.html',
                                 user=user,
                                 issue=issue,
                                 history=history,
                                 division_id=division_id)
    
    @app.route('/division/<int:division_id>/issues/<int:issue_id>/delete', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def delete_issue(division_id, issue_id):
        """Soft delete an issue (set is_active = 0)"""
        user = session.get('user')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE issues
                SET is_active = 0, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND division_id = ?
            """, (user['id'], issue_id, division_id))
            
            conn.commit()
        
        log_to_audit(
            user['id'], 'issues', issue_id, 'DELETE',
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )
        
        flash('Issue deleted successfully', 'success')
        return redirect(url_for('division_issues', division_id=division_id))
    
    @app.route('/division/<int:division_id>/issues/<int:issue_id>/convert-to-rock', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def convert_issue_to_rock(division_id, issue_id):
        """Convert an issue to a quarterly rock"""
        user = session.get('user')
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
        
        # Get the issue
        cursor.execute("""
            SELECT * FROM issues WHERE id = ? AND division_id = ?
        """, (issue_id, division_id))
        issue = dict(cursor.fetchone())
        
        # Calculate current quarter
        from datetime import datetime
        current_month = datetime.now().month
        current_quarter = (current_month - 1) // 3 + 1
        current_year = datetime.now().year
        
        # Create the rock
        cursor.execute("""
            INSERT INTO rocks (
                organization_id, division_id, description, owner, 
                quarter, year, status, progress, priority, 
                created_by, is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, 'NOT STARTED', 0, 1, ?, 1)
        """, (1, division_id, issue['issue'], issue['owner_name'] or 'Unassigned',
              current_quarter, current_year, user['id']))
        
        rock_id = cursor.lastrowid
        
        # Mark issue as resolved
        cursor.execute("""
            UPDATE issues
            SET status = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP,
                resolved_by = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        """, (user['id'], user['id'], issue_id))
        
        conn.commit()
        
        log_to_audit(
            user['id'], 'issues', issue_id, 'CONVERT_TO_ROCK',
            changes={'rock_id': rock_id, 'status': 'RESOLVED'},
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )
        
        log_to_audit(
            user['id'], 'rocks', rock_id, 'CREATE',
            changes={'source': 'issue', 'issue_id': issue_id},
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )
        
        flash(f'Issue converted to Rock successfully (Q{current_quarter} {current_year})', 'success')
        return redirect(url_for('division_issues', division_id=division_id))
    
    @app.route('/division/<int:division_id>/issues/<int:issue_id>/convert-to-todo', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def convert_issue_to_todo(division_id, issue_id):
        """Convert an issue to a todo"""
        user = session.get('user')
        resolve_issue = request.form.get('resolve_issue') == 'yes'
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get the issue
            cursor.execute("""
                SELECT * FROM issues WHERE id = ? AND division_id = ?
            """, (issue_id, division_id))
            issue = dict(cursor.fetchone())
            
            # Create the todo
            cursor.execute("""
                INSERT INTO todos (
                    organization_id, division_id, task, owner, 
                    status, source, source_issue_id, priority,
                    created_by, is_active
                )
                VALUES (?, ?, ?, ?, 'OPEN', 'ISSUE', ?, ?, ?, 1)
            """, (1, division_id, issue['issue'], issue['owner_name'] or 'Unassigned',
                  issue_id, issue['priority'], user['id']))
            
            todo_id = cursor.lastrowid
            
            # Optionally mark issue as resolved
            if resolve_issue:
                cursor.execute("""
                    UPDATE issues
                    SET status = 'RESOLVED', resolved_at = CURRENT_TIMESTAMP,
                        resolved_by = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (user['id'], user['id'], issue_id))
            
            conn.commit()
        
        log_to_audit(
            user['id'], 'issues', issue_id, 'CONVERT_TO_TODO',
            changes={'todo_id': todo_id, 'resolved': resolve_issue},
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )
        
        log_to_audit(
            user['id'], 'todos', todo_id, 'CREATE',
            changes={'source': 'issue', 'issue_id': issue_id},
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )
        
        flash('Issue converted to To-Do successfully', 'success')
        return redirect(url_for('division_issues', division_id=division_id))
    
    @app.route('/division/<int:division_id>/issues/<int:issue_id>/move', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def move_issue(division_id, issue_id):
        """Move an issue to a different division"""
        user = session.get('user')
        target_division_id = request.form.get('target_division_id', type=int)
        
        if not target_division_id:
            flash('Please select a target division', 'danger')
            return redirect(url_for('division_issues', division_id=division_id))
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Verify target division exists
            cursor.execute("SELECT display_name FROM divisions WHERE id = ?", (target_division_id,))
            target_division = cursor.fetchone()
            
            if not target_division:
                flash('Invalid target division', 'danger')
                return redirect(url_for('division_issues', division_id=division_id))
            
            target_name = dict(target_division)['display_name']
            
            # Move the issue
            cursor.execute("""
                UPDATE issues
                SET division_id = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND division_id = ?
            """, (target_division_id, user['id'], issue_id, division_id))
            
            conn.commit()
        
        log_to_audit(
            user['id'], 'issues', issue_id, 'MOVE',
            changes={'from_division': division_id, 'to_division': target_division_id},
            organization_id=1,
            division_id=target_division_id,
            ip_address=request.remote_addr
        )
        
        flash(f'Issue moved to {target_name} successfully', 'success')
        return redirect(url_for('division_issues', division_id=division_id))
    
    @app.route('/api/division/<int:division_id>/issues')
    @login_required
    @division_access_required('division_id')
    @retry_on_lock(max_retries=3)
    def api_issues(division_id):
        """Get issues as JSON"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT i.*, u.full_name as owner_full_name
                FROM issues i
                LEFT JOIN users u ON i.owner_user_id = u.id
                WHERE i.division_id = ? AND i.is_active = 1
                ORDER BY i.date_added DESC
            """, (division_id,))
            
            issues = [dict(row) for row in cursor.fetchall()]

            return jsonify(issues)

    @app.route('/division/<int:division_id>/issues/brainstorm')
    @login_required
    @division_access_required('division_id')
    def issue_brainstorm(division_id):
        """Brainstorm issues screen - rapid entry then IDS categorization"""
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

            # Get division users for owner assignment
            cursor.execute("""
                SELECT DISTINCT u.id, u.full_name
                FROM users u
                JOIN user_roles ur ON u.id = ur.user_id
                WHERE ur.division_id = ? AND u.is_active = 1
                ORDER BY u.full_name
            """, (division_id,))
            users = [dict(row) for row in cursor.fetchall()]

            can_edit = can_edit_division(user, division_id)

        return render_template('brainstorm.html',
                             user=user,
                             division=division,
                             users=users,
                             can_edit=can_edit)

    @app.route('/division/<int:division_id>/issues/brainstorm/add', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def brainstorm_add_issue(division_id):
        """Rapidly add an issue during brainstorm session"""
        user = session.get('user')
        data = request.get_json()

        if not data or not data.get('issue', '').strip():
            return jsonify({'error': 'Issue text is required'}), 400

        issue_text = data['issue'].strip()

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO issues (
                    organization_id, division_id, issue, category, priority,
                    owner, owner_name, date_added, status, ids_stage,
                    created_by, updated_by
                )
                VALUES (
                    (SELECT organization_id FROM divisions WHERE id = ?),
                    ?, ?, 'ADMINISTRATIVE', 'MEDIUM',
                    'Unassigned', NULL, ?, 'OPEN', 'IDENTIFY',
                    ?, ?
                )
            """, (division_id, division_id, issue_text,
                  datetime.now().strftime('%Y-%m-%d'),
                  user['id'], user['id']))

            issue_id = cursor.lastrowid
            conn.commit()

        log_to_audit(
            user['id'], 'issues', issue_id, 'CREATE',
            changes={'issue': issue_text, 'source': 'brainstorm'},
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )

        return jsonify({'success': True, 'id': issue_id, 'issue': issue_text})

    @app.route('/division/<int:division_id>/issues/brainstorm/process', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def brainstorm_process_issues(division_id):
        """Process brainstormed issues - categorize as Rock, To-Do, Table, or Resolve"""
        user = session.get('user')
        data = request.get_json()

        if not data or not data.get('items'):
            return jsonify({'error': 'No items to process'}), 400

        results = {'rocks': 0, 'todos': 0, 'tabled': 0, 'resolved': 0, 'errors': []}

        current_month = datetime.now().month
        current_quarter = (current_month - 1) // 3 + 1
        current_year = datetime.now().year

        with get_db_connection() as conn:
            cursor = conn.cursor()

            for item in data['items']:
                issue_id = item.get('id')
                action = item.get('action')  # rock, todo, table, resolve
                owner_name = item.get('owner', '')
                notes = item.get('notes', '')

                if not issue_id or not action:
                    continue

                try:
                    # Verify issue belongs to this division
                    cursor.execute("""
                        SELECT * FROM issues WHERE id = ? AND division_id = ? AND is_active = 1
                    """, (issue_id, division_id))
                    issue = cursor.fetchone()
                    if not issue:
                        results['errors'].append(f'Issue {issue_id} not found')
                        continue

                    issue = dict(issue)

                    # Update owner if provided
                    if owner_name:
                        cursor.execute("""
                            UPDATE issues SET owner_name = ?, owner = ?
                            WHERE id = ?
                        """, (owner_name, owner_name, issue_id))

                    if action == 'rock':
                        # Convert to Rock
                        cursor.execute("""
                            INSERT INTO rocks (
                                organization_id, division_id, description, owner,
                                quarter, year, status, progress, priority,
                                created_by, is_active
                            )
                            VALUES (?, ?, ?, ?, ?, ?, 'NOT STARTED', 0, 1, ?, 1)
                        """, (1, division_id, issue['issue'],
                              owner_name or issue.get('owner_name') or 'Unassigned',
                              current_quarter, current_year, user['id']))

                        rock_id = cursor.lastrowid

                        cursor.execute("""
                            UPDATE issues
                            SET status = 'RESOLVED', ids_stage = 'SOLVE',
                                solution = ?, resolved_at = CURRENT_TIMESTAMP,
                                resolved_by = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (f'Converted to Rock (Q{current_quarter} {current_year})',
                              user['id'], user['id'], issue_id))

                        results['rocks'] += 1

                    elif action == 'todo':
                        # Convert to To-Do
                        cursor.execute("""
                            INSERT INTO todos (
                                organization_id, division_id, task, owner,
                                status, source, source_issue_id, priority,
                                created_by, is_active
                            )
                            VALUES (?, ?, ?, ?, 'OPEN', 'ISSUE', ?, 'MEDIUM', ?, 1)
                        """, (1, division_id, issue['issue'],
                              owner_name or issue.get('owner_name') or 'Unassigned',
                              issue_id, user['id']))

                        cursor.execute("""
                            UPDATE issues
                            SET status = 'RESOLVED', ids_stage = 'SOLVE',
                                solution = 'Converted to To-Do',
                                resolved_at = CURRENT_TIMESTAMP,
                                resolved_by = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (user['id'], user['id'], issue_id))

                        results['todos'] += 1

                    elif action == 'table':
                        # Keep on issues list - update notes/owner if provided
                        cursor.execute("""
                            UPDATE issues
                            SET ids_stage = 'IDENTIFY',
                                discussion_notes = CASE WHEN ? != '' THEN ? ELSE discussion_notes END,
                                updated_by = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (notes, notes, user['id'], issue_id))

                        results['tabled'] += 1

                    elif action == 'resolve':
                        cursor.execute("""
                            UPDATE issues
                            SET status = 'RESOLVED', ids_stage = 'SOLVE',
                                solution = ?,
                                resolved_at = CURRENT_TIMESTAMP,
                                resolved_by = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                        """, (notes or 'Resolved during brainstorm session',
                              user['id'], user['id'], issue_id))

                        results['resolved'] += 1

                except Exception as e:
                    results['errors'].append(f'Error processing issue {issue_id}: {str(e)}')

            conn.commit()

        log_to_audit(
            user['id'], 'issues', 0, 'BRAINSTORM_PROCESS',
            changes=results,
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )

        return jsonify({'success': True, 'results': results})

    # =====================================================
    # AJAX API ENDPOINTS FOR LIVE INLINE EDITING
    # =====================================================

    @app.route('/api/division/<int:division_id>/issues/all')
    @login_required
    @division_access_required('division_id')
    @retry_on_lock(max_retries=3)
    def api_issues_all(division_id):
        """Get all issues as JSON (for live page)"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT i.*, u.full_name as owner_full_name
                FROM issues i
                LEFT JOIN users u ON i.owner_user_id = u.id
                WHERE i.division_id = ? AND i.is_active = 1
                ORDER BY
                    CASE i.priority WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 WHEN 'LOW' THEN 3 ELSE 4 END,
                    CASE i.status WHEN 'OPEN' THEN 1 WHEN 'IN PROGRESS' THEN 2 WHEN 'RESOLVED' THEN 3 ELSE 4 END,
                    i.date_added DESC
            """, (division_id,))
            issues = [dict(row) for row in cursor.fetchall()]
        return jsonify({'success': True, 'issues': issues})

    @app.route('/api/division/<int:division_id>/issues', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def api_add_issue(division_id):
        """Add an issue via AJAX"""
        user = session.get('user')
        data = request.get_json()
        issue_text = (data.get('issue') or '').strip()
        if not issue_text:
            return jsonify({'success': False, 'error': 'Issue text required'}), 400

        owner = data.get('owner', '')
        priority = data.get('priority', 'MEDIUM')
        category = data.get('category', 'ADMINISTRATIVE')

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT organization_id FROM divisions WHERE id = ?", (division_id,))
            org_id = cursor.fetchone()['organization_id']

            cursor.execute("""
                INSERT INTO issues (
                    organization_id, division_id, issue, category, priority,
                    owner, owner_name, date_added, status, ids_stage,
                    created_by, updated_by, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'OPEN', 'IDENTIFY', ?, ?, 1)
            """, (org_id, division_id, issue_text, category, priority,
                  owner, owner, datetime.now().strftime('%Y-%m-%d'),
                  user['id'], user['id']))
            issue_id = cursor.lastrowid
            conn.commit()

        log_to_audit(user['id'], 'issues', issue_id, 'CREATE',
                     changes={'issue': issue_text, 'source': 'live_page'},
                     organization_id=1, division_id=division_id,
                     ip_address=request.remote_addr)

        return jsonify({'success': True, 'issue_id': issue_id})

    @app.route('/api/division/<int:division_id>/issues/<int:issue_id>', methods=['PUT'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def api_update_issue(division_id, issue_id):
        """Update an issue field inline via AJAX"""
        user = session.get('user')
        data = request.get_json()
        allowed = ['issue', 'owner', 'priority', 'category', 'status',
                   'ids_stage', 'discussion_notes', 'solution', 'owner_name']

        with get_db_connection() as conn:
            cursor = conn.cursor()
            for field in allowed:
                if field in data:
                    cursor.execute(f"""
                        UPDATE issues SET {field} = ?, updated_by = ?,
                               updated_at = CURRENT_TIMESTAMP
                        WHERE id = ? AND division_id = ?
                    """, (data[field], user['id'], issue_id, division_id))

            # If status changed to RESOLVED, set resolved_at
            if data.get('status') == 'RESOLVED':
                cursor.execute("""
                    UPDATE issues SET resolved_at = CURRENT_TIMESTAMP,
                           resolved_by = ? WHERE id = ? AND division_id = ?
                """, (user['id'], issue_id, division_id))

            conn.commit()

        return jsonify({'success': True})

    @app.route('/api/division/<int:division_id>/issues/<int:issue_id>/resolve', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def api_resolve_issue(division_id, issue_id):
        """Toggle resolve/reopen an issue via AJAX"""
        user = session.get('user')
        data = request.get_json() or {}
        resolved = data.get('resolved', True)

        with get_db_connection() as conn:
            if resolved:
                conn.execute("""
                    UPDATE issues SET status = 'RESOLVED', ids_stage = 'SOLVE',
                           resolved_at = CURRENT_TIMESTAMP, resolved_by = ?,
                           updated_by = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND division_id = ?
                """, (user['id'], user['id'], issue_id, division_id))
            else:
                conn.execute("""
                    UPDATE issues SET status = 'OPEN', ids_stage = 'IDENTIFY',
                           resolved_at = NULL, resolved_by = NULL,
                           updated_by = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND division_id = ?
                """, (user['id'], issue_id, division_id))
            conn.commit()

        return jsonify({'success': True})

    @app.route('/api/division/<int:division_id>/issues/<int:issue_id>', methods=['DELETE'])
    @login_required
    @division_edit_required('division_id')
    @retry_on_lock(max_retries=5)
    def api_delete_issue(division_id, issue_id):
        """Soft-delete an issue via AJAX"""
        user = session.get('user')
        with get_db_connection() as conn:
            conn.execute("""
                UPDATE issues SET is_active = 0, updated_by = ?,
                       updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND division_id = ?
            """, (user['id'], issue_id, division_id))
            conn.commit()
        return jsonify({'success': True})
