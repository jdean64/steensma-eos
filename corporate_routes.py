"""
EOS Platform - Corporate Routes
Company-wide Vision/VTO, Accountability Chart, and Financial Rollup
"""

from flask import render_template, request, redirect, url_for, flash, jsonify, session
from auth import login_required, parent_admin_required, log_action
import sqlite3
import json
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def get_db():
    """Get database connection with timeout for concurrent access"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def get_financial_rollup():
    """Sum gross profit data across all divisions"""
    from financial_parser import parse_site_lead_statement
    rollup = {
        'new_equipment': {'month': 0, 'ytd': 0, 'py_month': 0, 'py_ytd': 0},
        'parts': {'month': 0, 'ytd': 0, 'py_month': 0, 'py_ytd': 0},
        'labor': {'month': 0, 'ytd': 0, 'py_month': 0, 'py_ytd': 0},
        'gross_profit': {'month': 0, 'ytd': 0, 'py_month': 0, 'py_ytd': 0},
        'by_division': {}
    }
    for name in ['Plainwell', 'Kalamazoo', 'Generator']:
        data = parse_site_lead_statement(division_name=name)
        rollup['by_division'][name] = data
        for cat in ['new_equipment', 'parts', 'labor', 'gross_profit']:
            for period in ['month', 'ytd', 'py_month', 'py_ytd']:
                rollup[cat][period] += data[cat][period]
    return rollup

def register_corporate_routes(app):
    """Register corporate-level routes"""

    @app.route('/corporate')
    @parent_admin_required
    def corporate_dashboard():
        """Corporate dashboard with Vision, Accountability, and Financial cards"""
        user = session.get('user')
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM organizations WHERE id = 1")
        organization = dict(cursor.fetchone())

        # VTO check
        cursor.execute("SELECT COUNT(*) as count FROM vto WHERE division_id IS NULL AND is_active = 1")
        vto_exists = cursor.fetchone()['count'] > 0

        # Accountability seats
        cursor.execute("SELECT COUNT(*) as count FROM accountability_chart WHERE division_id IS NULL AND is_active = 1")
        accountability_count = cursor.fetchone()['count']

        conn.close()

        # Financial rollup
        try:
            rollup = get_financial_rollup()
        except Exception:
            rollup = None

        return render_template('corporate_dashboard.html',
                             user=user,
                             organization=organization,
                             vto_exists=vto_exists,
                             accountability_count=accountability_count,
                             rollup=rollup)

    # ---- Vision/VTO ----

    @app.route('/corporate/vision')
    @parent_admin_required
    def corporate_vision():
        """View/edit corporate Vision/VTO"""
        user = session.get('user')
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM organizations WHERE id = 1")
        organization = dict(cursor.fetchone())

        cursor.execute("""
            SELECT * FROM vto
            WHERE division_id IS NULL AND is_active = 1
            ORDER BY updated_at DESC LIMIT 1
        """)
        vto_row = cursor.fetchone()
        vto = dict(vto_row) if vto_row else None
        core_values = []
        if vto and vto.get('core_values'):
            try:
                core_values = json.loads(vto['core_values'])
            except Exception:
                core_values = []

        conn.close()

        return render_template('corporate_vision.html',
                             user=user,
                             organization=organization,
                             vto=vto,
                             core_values=core_values)

    @app.route('/corporate/vision/update', methods=['POST'])
    @parent_admin_required
    def corporate_vision_update():
        """Update corporate VTO fields"""
        user = session.get('user')
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400

        conn = get_db()
        cursor = conn.cursor()

        allowed_fields = [
            'ten_year_target', 'core_values', 'core_purpose', 'core_niche',
            'target_market', 'unique_value_proposition', 'proven_process', 'guarantee',
            'three_year_revenue', 'three_year_profit', 'three_year_measurables',
            'one_year_revenue', 'one_year_profit', 'one_year_goals'
        ]

        updates = []
        params = []
        changes = {}
        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(data[field])
                changes[field] = data[field]

        if updates:
            updates.append("updated_at = CURRENT_TIMESTAMP")
            cursor.execute(f"""
                UPDATE vto SET {', '.join(updates)}
                WHERE division_id IS NULL AND is_active = 1
            """, params)

            log_action(
                user['id'], 'vto', None, 'UPDATE',
                changes=changes,
                organization_id=1,
                ip_address=request.remote_addr
            )
            conn.commit()

        conn.close()
        return jsonify({'success': True})

    # ---- Accountability ----

    @app.route('/corporate/accountability')
    @parent_admin_required
    def corporate_accountability():
        """Corporate accountability chart"""
        user = session.get('user')
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM organizations WHERE id = 1")
        organization = dict(cursor.fetchone())

        cursor.execute("""
            SELECT
                ac.id, ac.seat_name, ac.seat_description,
                ac.user_id, ac.user_name,
                ac.role_1, ac.role_2, ac.role_3, ac.role_4, ac.role_5,
                ac.reports_to_seat_id,
                ac.gwc_get_it, ac.gwc_want_it, ac.gwc_capacity,
                ac.division_id,
                parent.seat_name as reports_to_name
            FROM accountability_chart ac
            LEFT JOIN accountability_chart parent ON ac.reports_to_seat_id = parent.id
            WHERE ac.division_id IS NULL AND ac.is_active = 1
            ORDER BY ac.reports_to_seat_id IS NULL DESC, ac.reports_to_seat_id, ac.id
        """)
        seats = [dict(row) for row in cursor.fetchall()]

        seat_map = {}
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
            seat['children'] = []
            seat_map[seat['id']] = seat

        root_seats = []
        for seat in seats:
            parent_id = seat.get('reports_to_seat_id')
            if parent_id and parent_id in seat_map:
                seat_map[parent_id]['children'].append(seat)
            else:
                root_seats.append(seat)

        total = len(seats)
        filled = len([s for s in seats if s['is_filled']])

        summary = {
            'total': total,
            'filled': filled,
            'open': total - filled,
        }

        # Get division site leads for reference
        cursor.execute("""
            SELECT ac.seat_name, ac.user_name, d.display_name as division_name, d.id as div_id
            FROM accountability_chart ac
            JOIN divisions d ON ac.division_id = d.id
            WHERE ac.seat_name LIKE '%Site Lead%' AND ac.is_active = 1 AND d.is_active = 1
        """)
        site_leads = [dict(row) for row in cursor.fetchall()]

        conn.close()

        return render_template('corporate_accountability.html',
                             user=user,
                             organization=organization,
                             seats=seats,
                             root_seats=root_seats,
                             summary=summary,
                             site_leads=site_leads)

    @app.route('/corporate/accountability/add', methods=['POST'])
    @parent_admin_required
    def corporate_add_seat():
        """Add a company-level seat"""
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
            return redirect(url_for('corporate_accountability'))

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO accountability_chart (
                organization_id, division_id, seat_name, seat_description,
                user_name, reports_to_seat_id, role_1, role_2, role_3,
                gwc_get_it, gwc_want_it, gwc_capacity,
                updated_by, is_active
            ) VALUES (1, NULL, ?, ?, ?, ?, ?, ?, ?, 0, 0, 0, ?, 1)
        """, (seat_name, seat_description, user_name,
              reports_to or None, role_1, role_2, role_3, user['id']))

        log_action(user['id'], 'accountability_chart', cursor.lastrowid, 'CREATE',
                   changes={'seat_name': seat_name, 'user_name': user_name},
                   organization_id=1, ip_address=request.remote_addr)
        conn.commit()
        conn.close()

        flash(f'Seat "{seat_name}" added', 'success')
        return redirect(url_for('corporate_accountability'))

    @app.route('/corporate/accountability/<int:seat_id>/update', methods=['POST'])
    @parent_admin_required
    def corporate_update_seat(seat_id):
        """Update a company-level seat"""
        user = session.get('user')
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data'}), 400

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM accountability_chart WHERE id = ? AND division_id IS NULL", (seat_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({'error': 'Seat not found'}), 404

        allowed = ['seat_name', 'seat_description', 'user_name', 'user_id',
                    'reports_to_seat_id', 'role_1', 'role_2', 'role_3', 'role_4', 'role_5',
                    'gwc_get_it', 'gwc_want_it', 'gwc_capacity']
        updates = []
        params = []
        changes = {}
        for field in allowed:
            if field in data:
                updates.append(f"{field} = ?")
                params.append(data[field])
                changes[field] = data[field]

        if updates:
            updates.append("updated_by = ?")
            params.append(user['id'])
            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(seat_id)
            cursor.execute(f"""
                UPDATE accountability_chart SET {', '.join(updates)}
                WHERE id = ? AND division_id IS NULL
            """, params)

            log_action(user['id'], 'accountability_chart', seat_id, 'UPDATE',
                       changes=changes, organization_id=1, ip_address=request.remote_addr)
            conn.commit()

        conn.close()
        return jsonify({'success': True})

    @app.route('/corporate/accountability/<int:seat_id>/delete', methods=['POST'])
    @parent_admin_required
    def corporate_delete_seat(seat_id):
        """Soft-delete a company-level seat"""
        user = session.get('user')
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE accountability_chart
            SET is_active = 0, updated_by = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND division_id IS NULL
        """, (user['id'], seat_id))

        log_action(user['id'], 'accountability_chart', seat_id, 'DELETE',
                   organization_id=1, ip_address=request.remote_addr)
        conn.commit()
        conn.close()

        flash('Seat removed', 'success')
        return redirect(url_for('corporate_accountability'))
