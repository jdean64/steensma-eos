"""
EOS Platform - Accountability Chart Routes
Organizational structure with seats, GWC assessment, and hierarchy
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, division_access_required, division_edit_required, log_action, can_edit_division
import sqlite3
from pathlib import Path

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

        # Get accountability chart seats with parent info
        cursor.execute("""
            SELECT
                ac.id, ac.seat_name, ac.seat_description,
                ac.user_id, ac.user_name,
                ac.role_1, ac.role_2, ac.role_3, ac.role_4, ac.role_5,
                ac.reports_to_seat_id,
                ac.gwc_get_it, ac.gwc_want_it, ac.gwc_capacity,
                parent.seat_name as reports_to_name
            FROM accountability_chart ac
            LEFT JOIN accountability_chart parent ON ac.reports_to_seat_id = parent.id
            WHERE ac.division_id = ? AND ac.is_active = 1
            ORDER BY ac.reports_to_seat_id IS NULL DESC, ac.reports_to_seat_id, ac.seat_name
        """, (division_id,))

        seats = [dict(row) for row in cursor.fetchall()]

        # Build roles list for each seat
        for seat in seats:
            roles = []
            for i in range(1, 6):
                r = seat.get(f'role_{i}')
                if r:
                    roles.append(r)
            seat['roles'] = roles
            seat['is_filled'] = bool(seat.get('user_name'))
            seat['gwc_score'] = sum([
                1 if seat.get('gwc_get_it') else 0,
                1 if seat.get('gwc_want_it') else 0,
                1 if seat.get('gwc_capacity') else 0,
            ])

        # Summary
        total = len(seats)
        filled = len([s for s in seats if s['is_filled']])
        gwc_full = len([s for s in seats if s['gwc_score'] == 3 and s['is_filled']])

        summary = {
            'total': total,
            'filled': filled,
            'open': total - filled,
            'right_seat': gwc_full,
        }

        # Get users for seat assignment
        cursor.execute("""
            SELECT DISTINCT u.id, u.full_name
            FROM users u
            JOIN user_roles ur ON u.id = ur.user_id
            WHERE ur.division_id = ? AND u.is_active = 1
            ORDER BY u.full_name
        """, (division_id,))
        users = [dict(row) for row in cursor.fetchall()]

        conn.close()

        can_edit = can_edit_division(user, division_id)

        return render_template('accountability.html',
                             user=user,
                             division=division,
                             seats=seats,
                             summary=summary,
                             users=users,
                             can_edit=can_edit)

    @app.route('/division/<int:division_id>/accountability/add', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def add_seat(division_id):
        """Add a new seat to the accountability chart"""
        user = session.get('user')

        seat_name = request.form.get('seat_name', '').strip()
        seat_description = request.form.get('seat_description', '').strip()
        user_name = request.form.get('user_name', '').strip() or None
        reports_to = request.form.get('reports_to_seat_id', type=int)
        role_1 = request.form.get('role_1', '').strip() or None
        role_2 = request.form.get('role_2', '').strip() or None
        role_3 = request.form.get('role_3', '').strip() or None

        if not seat_name:
            flash('Seat name is required', 'danger')
            return redirect(url_for('division_accountability', division_id=division_id))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO accountability_chart (
                organization_id, division_id, seat_name, seat_description,
                user_name, reports_to_seat_id, role_1, role_2, role_3,
                gwc_get_it, gwc_want_it, gwc_capacity,
                updated_by, is_active
            )
            VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, 1)
        """, (division_id, seat_name, seat_description, user_name,
              reports_to or None, role_1, role_2, role_3, user['id']))

        seat_id = cursor.lastrowid

        log_action(
            user['id'], 'accountability_chart', seat_id, 'CREATE',
            changes={'seat_name': seat_name, 'user_name': user_name},
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )

        conn.commit()
        conn.close()

        flash(f'Seat "{seat_name}" added', 'success')
        return redirect(url_for('division_accountability', division_id=division_id))

    @app.route('/division/<int:division_id>/accountability/<int:seat_id>/update', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def update_seat(division_id, seat_id):
        """Update a seat (JSON for inline edits)"""
        user = session.get('user')
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data'}), 400

        conn = get_db()
        cursor = conn.cursor()

        # Verify seat belongs to division
        cursor.execute("""
            SELECT * FROM accountability_chart WHERE id = ? AND division_id = ?
        """, (seat_id, division_id))
        seat = cursor.fetchone()
        if not seat:
            conn.close()
            return jsonify({'error': 'Seat not found'}), 404

        updates = []
        params = []
        changes = {}

        allowed_fields = [
            'seat_name', 'seat_description', 'user_name', 'user_id',
            'reports_to_seat_id', 'role_1', 'role_2', 'role_3', 'role_4', 'role_5',
            'gwc_get_it', 'gwc_want_it', 'gwc_capacity'
        ]

        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(data[field])
                changes[field] = data[field]

        if updates:
            updates.append("updated_by = ?")
            params.append(user['id'])
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.extend([seat_id, division_id])

            cursor.execute(f"""
                UPDATE accountability_chart
                SET {', '.join(updates)}
                WHERE id = ? AND division_id = ?
            """, params)

            log_action(
                user['id'], 'accountability_chart', seat_id, 'UPDATE',
                changes=changes,
                organization_id=1,
                division_id=division_id,
                ip_address=request.remote_addr
            )

            conn.commit()

        conn.close()
        return jsonify({'success': True})

    @app.route('/division/<int:division_id>/accountability/<int:seat_id>/delete', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def delete_seat(division_id, seat_id):
        """Soft-delete a seat"""
        user = session.get('user')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE accountability_chart
            SET is_active = 0, updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND division_id = ?
        """, (user['id'], seat_id, division_id))

        log_action(
            user['id'], 'accountability_chart', seat_id, 'DELETE',
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )

        conn.commit()
        conn.close()

        flash('Seat removed', 'success')
        return redirect(url_for('division_accountability', division_id=division_id))
