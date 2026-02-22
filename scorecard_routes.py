"""
EOS Platform - Scorecard Routes
Weekly measurables and metrics tracking with gross profit display
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
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA synchronous=NORMAL')
    conn.execute('PRAGMA busy_timeout=30000')
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

        # Get gross profit data
        gross_profit = None
        try:
            from financial_parser import parse_site_lead_statement
            gross_profit = parse_site_lead_statement(division_name=division['name'])
        except Exception:
            pass

        # Get users for owner dropdown
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

        return render_template('scorecard.html',
                             user=user,
                             division=division,
                             metrics=metrics,
                             summary=summary,
                             gross_profit=gross_profit,
                             users=users,
                             can_edit=can_edit)

    @app.route('/division/<int:division_id>/scorecard/add', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def add_scorecard_metric(division_id):
        """Add a new scorecard metric"""
        user = session.get('user')

        metric_name = request.form.get('metric', '').strip()
        owner = request.form.get('owner', '').strip()
        goal = request.form.get('goal', '').strip()

        if not metric_name or not owner:
            flash('Metric name and owner are required', 'danger')
            return redirect(url_for('division_scorecard', division_id=division_id))

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT organization_id FROM divisions WHERE id = ?", (division_id,))
        org_id = cursor.fetchone()['organization_id']

        cursor.execute("""
            INSERT INTO scorecard_metrics (
                metric, owner, goal, status, quarter,
                is_active, organization_id, division_id
            ) VALUES (?, ?, ?, 'YELLOW', ?, 1, ?, ?)
        """, (metric_name, owner, goal,
              f"Q1 {datetime.now().year}", org_id, division_id))

        log_action(
            user['id'], 'scorecard_metrics', cursor.lastrowid, 'CREATE',
            changes={'metric': metric_name, 'owner': owner, 'goal': goal},
            organization_id=org_id,
            division_id=division_id,
            ip_address=request.remote_addr
        )

        conn.commit()
        conn.close()

        flash(f'Metric "{metric_name}" added', 'success')
        return redirect(url_for('division_scorecard', division_id=division_id))

    @app.route('/division/<int:division_id>/scorecard/<int:metric_id>/update', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def update_scorecard_metric(division_id, metric_id):
        """Update a scorecard metric's weekly value or status"""
        user = session.get('user')

        conn = get_db()
        cursor = conn.cursor()

        # Verify metric belongs to this division
        cursor.execute("""
            SELECT * FROM scorecard_metrics
            WHERE id = ? AND division_id = ?
        """, (metric_id, division_id))
        metric = cursor.fetchone()
        if not metric:
            conn.close()
            return jsonify({'error': 'Metric not found'}), 404

        data = request.get_json() if request.is_json else None
        if data:
            # JSON update (from inline editing)
            updates = []
            params = []
            changes = {}

            for field in ['status', 'goal', 'owner',
                          'week_1', 'week_2', 'week_3', 'week_4',
                          'week_5', 'week_6', 'week_7', 'week_8',
                          'week_9', 'week_10', 'week_11', 'week_12', 'week_13']:
                if field in data:
                    updates.append(f"{field} = ?")
                    params.append(data[field])
                    changes[field] = data[field]

            if updates:
                params.extend([metric_id, division_id])
                cursor.execute(f"""
                    UPDATE scorecard_metrics
                    SET {', '.join(updates)}
                    WHERE id = ? AND division_id = ?
                """, params)

                log_action(
                    user['id'], 'scorecard_metrics', metric_id, 'UPDATE',
                    changes=changes,
                    organization_id=metric['organization_id'],
                    division_id=division_id,
                    ip_address=request.remote_addr
                )

                conn.commit()

            conn.close()
            return jsonify({'success': True})
        else:
            # Form update
            status = request.form.get('status', metric['status'])
            goal = request.form.get('goal', metric['goal'])

            cursor.execute("""
                UPDATE scorecard_metrics
                SET status = ?, goal = ?
                WHERE id = ? AND division_id = ?
            """, (status, goal, metric_id, division_id))

            conn.commit()
            conn.close()

            flash('Metric updated', 'success')
            return redirect(url_for('division_scorecard', division_id=division_id))

    @app.route('/division/<int:division_id>/scorecard/<int:metric_id>/delete', methods=['POST'])
    @login_required
    @division_edit_required('division_id')
    def delete_scorecard_metric(division_id, metric_id):
        """Soft-delete a scorecard metric"""
        user = session.get('user')

        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE scorecard_metrics
            SET is_active = 0
            WHERE id = ? AND division_id = ?
        """, (metric_id, division_id))

        log_action(
            user['id'], 'scorecard_metrics', metric_id, 'DELETE',
            changes={'is_active': 0},
            organization_id=1,
            division_id=division_id,
            ip_address=request.remote_addr
        )

        conn.commit()
        conn.close()

        flash('Metric removed', 'success')
        return redirect(url_for('division_scorecard', division_id=division_id))

    @app.route('/api/division/<int:division_id>/gross_profit')
    @login_required
    @division_access_required('division_id')
    def get_gross_profit_data(division_id):
        """API endpoint to fetch gross profit data from Site Lead file"""
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM divisions WHERE id = ?", (division_id,))
            row = cursor.fetchone()
            conn.close()
            division_name = row['name'] if row else None

            from financial_parser import parse_site_lead_statement
            data = parse_site_lead_statement(division_name=division_name)
            return jsonify(data)
        except Exception as e:
            return jsonify({
                'error': str(e),
                'new_equipment': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
                'parts': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
                'labor': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0},
                'gross_profit': {'month': 0.0, 'ytd': 0.0, 'py_month': 0.0, 'py_ytd': 0.0}
            }), 200
