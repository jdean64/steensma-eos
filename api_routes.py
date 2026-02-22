"""
EOS Platform - API endpoints for editing and IDS workflow
"""
import sqlite3
import json
from datetime import datetime
from flask import request, jsonify
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def log_change(table_name, record_id, action, changed_by, changes, ip_address=None):
    """Log all changes to audit_log table"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO audit_log (table_name, record_id, action, changed_by, changes, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (table_name, record_id, action, changed_by, json.dumps(changes), ip_address))
    
    conn.commit()
    conn.close()

def update_rock(rock_id, field, new_value, changed_by):
    """Update a rock field and track the change"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    cursor = conn.cursor()
    
    # Get current value
    cursor.execute(f'SELECT {field} FROM rocks WHERE id = ?', (rock_id,))
    old_value = cursor.fetchone()[0] if cursor.fetchone() else None
    
    # Update the field
    cursor.execute(f'''
        UPDATE rocks 
        SET {field} = ?, updated_at = ?, updated_by = ?
        WHERE id = ?
    ''', (new_value, datetime.now(), changed_by, rock_id))
    
    # Log to history
    cursor.execute('''
        INSERT INTO rocks_history (rock_id, field_changed, old_value, new_value, changed_by)
        VALUES (?, ?, ?, ?, ?)
    ''', (rock_id, field, str(old_value), str(new_value), changed_by))
    
    conn.commit()
    conn.close()
    
    # Log to audit
    log_change('rocks', rock_id, 'UPDATE', changed_by, {
        'field': field,
        'old_value': old_value,
        'new_value': new_value
    })

def ids_workflow_issue(issue_id, stage, changed_by, notes=None, solution=None):
    """
    Move issue through IDS workflow:
    1. IDENTIFY - Issue is recognized
    2. DISCUSS - Team discusses root cause and options
    3. SOLVE - Solution is implemented
    """
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    cursor = conn.cursor()
    
    # Get current stage
    cursor.execute('SELECT ids_stage FROM issues WHERE id = ?', (issue_id,))
    old_stage = cursor.fetchone()[0]
    
    updates = {'ids_stage': stage, 'updated_at': datetime.now()}
    
    if notes:
        updates['discussion_notes'] = notes
    
    if solution:
        updates['solution'] = solution
    
    if stage == 'SOLVE':
        updates['status'] = 'RESOLVED'
        updates['resolved_at'] = datetime.now()
    
    # Build dynamic UPDATE query
    set_clause = ', '.join([f'{k} = ?' for k in updates.keys()])
    values = list(updates.values()) + [issue_id]
    
    cursor.execute(f'UPDATE issues SET {set_clause} WHERE id = ?', values)
    
    # Log to history
    cursor.execute('''
        INSERT INTO issues_history (issue_id, field_changed, old_value, new_value, changed_by, change_note)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (issue_id, 'ids_stage', old_stage, stage, changed_by, notes or ''))
    
    conn.commit()
    conn.close()
    
    # Log to audit
    log_change('issues', issue_id, 'IDS_WORKFLOW', changed_by, {
        'old_stage': old_stage,
        'new_stage': stage,
        'notes': notes,
        'solution': solution
    })

def get_rock_history(rock_id):
    """Get full history of changes for a rock"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT field_changed, old_value, new_value, changed_by, changed_at, change_note
        FROM rocks_history
        WHERE rock_id = ?
        ORDER BY changed_at DESC
    ''', (rock_id,))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            'field': row[0],
            'old_value': row[1],
            'new_value': row[2],
            'changed_by': row[3],
            'changed_at': row[4],
            'note': row[5]
        })
    
    conn.close()
    return history

def get_issue_history(issue_id):
    """Get full IDS workflow history for an issue"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT field_changed, old_value, new_value, changed_by, changed_at, change_note
        FROM issues_history
        WHERE issue_id = ?
        ORDER BY changed_at ASC
    ''', (issue_id,))
    
    history = []
    for row in cursor.fetchall():
        history.append({
            'field': row[0],
            'old_value': row[1],
            'new_value': row[2],
            'changed_by': row[3],
            'changed_at': row[4],
            'note': row[5]
        })
    
    conn.close()
    return history

# Flask route helpers to add to app.py:

def add_api_routes(app):
    """Add these routes to your Flask app"""
    
    @app.route('/api/rocks/<int:rock_id>', methods=['PUT'])
    def update_rock_api(rock_id):
        """Update a rock field"""
        data = request.json
        field = data.get('field')
        value = data.get('value')
        changed_by = data.get('changed_by', 'System')
        
        try:
            update_rock(rock_id, field, value, changed_by)
            return jsonify({'success': True, 'message': 'Rock updated'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    
    @app.route('/api/rocks/<int:rock_id>/history', methods=['GET'])
    def get_rock_history_api(rock_id):
        """Get rock change history"""
        try:
            history = get_rock_history(rock_id)
            return jsonify({'success': True, 'history': history})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    
    @app.route('/api/issues/<int:issue_id>/ids', methods=['POST'])
    def ids_workflow_api(issue_id):
        """Move issue through IDS workflow"""
        data = request.json
        stage = data.get('stage')  # IDENTIFY, DISCUSS, or SOLVE
        changed_by = data.get('changed_by', 'System')
        notes = data.get('notes')
        solution = data.get('solution')
        
        try:
            ids_workflow_issue(issue_id, stage, changed_by, notes, solution)
            return jsonify({'success': True, 'message': f'Issue moved to {stage} stage'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
    
    @app.route('/api/issues/<int:issue_id>/history', methods=['GET'])
    def get_issue_history_api(issue_id):
        """Get issue IDS workflow history"""
        try:
            history = get_issue_history(issue_id)
            return jsonify({'success': True, 'history': history})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 400
