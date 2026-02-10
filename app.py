"""
Steensma EOS Strategic Platform
Vision/Traction Organizer, Rocks, Scorecard, Issues, To-Dos, Meetings
"""
import os
import sqlite3
from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
import json
import warnings
warnings.filterwarnings('ignore')

app = Flask(__name__)

# Database configuration
DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

# Configuration
DATASHEETS_DIR = os.path.join(os.path.dirname(__file__), 'datasheets')
ARCHIVE_DIR = os.path.join(os.path.dirname(__file__), 'archive')

def get_latest_file(patterns):
    """Get the most recent file matching one or more patterns"""
    if isinstance(patterns, str):
        patterns = [patterns]
    patterns = [p.lower() for p in patterns]
    files = [
        f for f in os.listdir(DATASHEETS_DIR)
        if any(p in f.lower() for p in patterns)
    ]
    if not files:
        return None
    latest = max(files, key=lambda f: os.path.getmtime(os.path.join(DATASHEETS_DIR, f)))
    return os.path.join(DATASHEETS_DIR, latest)

def parse_rocks(filepath):
    """
    Parse Quarterly Rocks CSV
    Format: Description|Owner|Status|DueDate|Progress
    """
    try:
        df = pd.read_csv(filepath, delimiter='|')
        rocks = []
        for _, row in df.iterrows():
            rocks.append({
                'description': str(row.get('Description', '')).strip(),
                'owner': str(row.get('Owner', '')).strip(),
                'status': str(row.get('Status', 'NOT STARTED')).strip(),
                'due_date': str(row.get('DueDate', '')).strip(),
                'progress': int(row.get('Progress', 0)) if pd.notna(row.get('Progress')) else 0
            })
        
        # Calculate summary metrics
        total = len(rocks)
        complete = len([r for r in rocks if r['status'].upper() == 'COMPLETE'])
        on_track = len([r for r in rocks if r['status'].upper() in ['COMPLETE', 'ON TRACK']])
        at_risk = len([r for r in rocks if r['status'].upper() in ['AT RISK', 'BLOCKED']])
        
        return {
            'rocks': rocks,
            'summary': {
                'total': total,
                'complete': complete,
                'on_track': on_track,
                'at_risk': at_risk,
                'completion_pct': round((on_track / total * 100) if total > 0 else 0, 1)
            }
        }
    except Exception as e:
        print(f"Error parsing rocks: {e}")
        return {'rocks': [], 'summary': {'total': 0, 'complete': 0, 'on_track': 0, 'at_risk': 0, 'completion_pct': 0}}

def parse_scorecard(filepath):
    """
    Parse Weekly Scorecard CSV
    Format: Metric|Owner|Goal|Week1|Week2|...|Week13|Status
    """
    try:
        df = pd.read_csv(filepath, delimiter='|')
        metrics = []
        
        for _, row in df.iterrows():
            # Get week columns (Week1 through Week13)
            weeks = []
            for i in range(1, 14):
                week_col = f'Week{i}'
                if week_col in row:
                    val = row[week_col]
                    weeks.append(float(val) if pd.notna(val) else None)
            
            metrics.append({
                'metric': str(row.get('Metric', '')).strip(),
                'owner': str(row.get('Owner', '')).strip(),
                'goal': str(row.get('Goal', '')).strip(),
                'weeks': weeks,
                'status': str(row.get('Status', 'YELLOW')).strip().upper()
            })
        
        # Calculate summary
        green = len([m for m in metrics if m['status'] == 'GREEN'])
        yellow = len([m for m in metrics if m['status'] == 'YELLOW'])
        red = len([m for m in metrics if m['status'] == 'RED'])
        
        return {
            'metrics': metrics,
            'summary': {
                'total': len(metrics),
                'green': green,
                'yellow': yellow,
                'red': red
            }
        }
    except Exception as e:
        print(f"Error parsing scorecard: {e}")
        return {'metrics': [], 'summary': {'total': 0, 'green': 0, 'yellow': 0, 'red': 0}}

def parse_issues(filepath):
    """
    Parse Issues List CSV
    Format: Issue|Priority|Owner|DateAdded|Status
    """
    try:
        df = pd.read_csv(filepath, delimiter='|')
        issues = []
        
        for _, row in df.iterrows():
            status = str(row.get('Status', 'OPEN')).strip().upper()
            if status in ['OPEN', 'IN PROGRESS']:  # Only show open issues
                issues.append({
                    'issue': str(row.get('Issue', '')).strip(),
                    'priority': str(row.get('Priority', 'MEDIUM')).strip().upper(),
                    'owner': str(row.get('Owner', '')).strip(),
                    'date_added': str(row.get('DateAdded', '')).strip(),
                    'status': status
                })
        
        # Calculate summary
        high = len([i for i in issues if i['priority'] == 'HIGH'])
        medium = len([i for i in issues if i['priority'] == 'MEDIUM'])
        low = len([i for i in issues if i['priority'] == 'LOW'])
        
        return {
            'issues': issues,
            'summary': {
                'total': len(issues),
                'high': high,
                'medium': medium,
                'low': low
            }
        }
    except Exception as e:
        print(f"Error parsing issues: {e}")
        return {'issues': [], 'summary': {'total': 0, 'high': 0, 'medium': 0, 'low': 0}}

def parse_todos(filepath):
    """
    Parse To-Dos CSV
    Format: Task|Owner|DueDate|Status|Source
    """
    try:
        df = pd.read_csv(filepath, delimiter='|')
        todos = []
        
        today = datetime.now().date()
        
        for _, row in df.iterrows():
            status = str(row.get('Status', 'OPEN')).strip().upper()
            if status != 'COMPLETE':
                due_str = str(row.get('DueDate', '')).strip()
                try:
                    due_date = datetime.strptime(due_str, '%m/%d/%Y').date()
                    is_overdue = due_date < today
                    days_until = (due_date - today).days
                except:
                    due_date = None
                    is_overdue = False
                    days_until = None
                
                todos.append({
                    'task': str(row.get('Task', '')).strip(),
                    'owner': str(row.get('Owner', '')).strip(),
                    'due_date': due_str,
                    'status': status,
                    'source': str(row.get('Source', '')).strip(),
                    'is_overdue': is_overdue,
                    'days_until': days_until
                })
        
        # Calculate summary
        this_week = len([t for t in todos if t['days_until'] is not None and 0 <= t['days_until'] <= 7])
        overdue = len([t for t in todos if t['is_overdue']])
        
        return {
            'todos': todos,
            'summary': {
                'total': len(todos),
                'this_week': this_week,
                'overdue': overdue
            }
        }
    except Exception as e:
        print(f"Error parsing todos: {e}")
        return {'todos': [], 'summary': {'total': 0, 'this_week': 0, 'overdue': 0}}

def parse_vto(filepath):
    """
    Parse Vision/Traction Organizer CSV
    Format: Section|Content
    """
    try:
        df = pd.read_csv(filepath, delimiter='|')
        vto = {}
        
        for _, row in df.iterrows():
            section = str(row.get('Section', '')).strip()
            content = str(row.get('Content', '')).strip()
            vto[section] = content
        
        return vto
    except Exception as e:
        print(f"Error parsing VTO: {e}")
        return {}

def parse_accountability_chart(filepath):
    """
    Parse Accountability Chart CSV
    Format: Seat|Accountabilities|Person|Roles
    """
    try:
        df = pd.read_csv(filepath, delimiter='|')
        seats = []
        
        for _, row in df.iterrows():
            seats.append({
                'seat': str(row.get('Seat', '')).strip(),
                'accountabilities': str(row.get('Accountabilities', '')).strip(),
                'person': str(row.get('Person', '')).strip(),
                'roles': str(row.get('Roles', '')).strip()
            })
        
        # Calculate summary
        filled = len([s for s in seats if s['person'] and s['person'] != 'Open'])
        open_seats = len(seats) - filled
        
        return {
            'seats': seats,
            'summary': {
                'total': len(seats),
                'filled': filled,
                'open': open_seats
            }
        }
    except Exception as e:
        print(f"Error parsing accountability chart: {e}")
        return {'seats': [], 'summary': {'total': 0, 'filled': 0, 'open': 0}}

@app.route('/')
def index():
    """Main EOS landing page with 6 metric cards"""
    return render_template('landing.html')

@app.route('/rocks')
def rocks():
    """Detailed Rocks page"""
    return render_template('rocks.html')

@app.route('/scorecard')
def scorecard():
    """Detailed Scorecard page"""
    return render_template('scorecard.html')

@app.route('/issues')
def issues():
    """Detailed Issues page"""
    return render_template('issues.html')

@app.route('/todos')
def todos():
    """Detailed To-Dos page"""
    return render_template('todos.html')

@app.route('/vision')
def vision():
    """Vision/Traction Organizer page"""
    return render_template('vision.html')

@app.route('/accountability')
def accountability():
    """Accountability Chart page"""
    return render_template('accountability.html')

@app.route('/meeting')
def meeting():
    """L10 Meeting page"""
    return render_template('meeting.html')

@app.route('/api/summary')
def get_summary():
    """API endpoint for landing page summary cards"""
    
    # Get latest files
    rocks_file = get_latest_file('rocks')
    scorecard_file = get_latest_file('scorecard')
    issues_file = get_latest_file('issues')
    todos_file = get_latest_file('todos')
    vto_file = get_latest_file('vto')
    accountability_file = get_latest_file('accountability')
    
    summary = {
        'timestamp': datetime.now().isoformat(),
        'rocks': {'total': 0, 'on_track': 0, 'completion_pct': 0},
        'scorecard': {'total': 0, 'green': 0, 'yellow': 0, 'red': 0},
        'issues': {'total': 0, 'high': 0},
        'todos': {'total': 0, 'this_week': 0, 'overdue': 0},
        'vision': {'quarter': 'Q1 2026'},
        'people': {'filled': 0, 'open': 0}
    }
    
    # Parse Rocks
    if rocks_file:
        rocks_data = parse_rocks(rocks_file)
        summary['rocks'] = rocks_data['summary']
    
    # Parse Scorecard
    if scorecard_file:
        scorecard_data = parse_scorecard(scorecard_file)
        summary['scorecard'] = scorecard_data['summary']
    
    # Parse Issues
    if issues_file:
        issues_data = parse_issues(issues_file)
        summary['issues'] = issues_data['summary']
    
    # Parse To-Dos
    if todos_file:
        todos_data = parse_todos(todos_file)
        summary['todos'] = todos_data['summary']
    
    # Parse VTO
    if vto_file:
        vto_data = parse_vto(vto_file)
        summary['vision']['quarter'] = vto_data.get('Quarter', 'Q1 2026')
    
    # Parse Accountability Chart
    if accountability_file:
        accountability_data = parse_accountability_chart(accountability_file)
        summary['people'] = accountability_data['summary']
    
    return jsonify(summary)

@app.route('/api/data')
def get_data():
    """API endpoint to fetch all EOS data"""
    
    # Get latest files
    rocks_file = get_latest_file('rocks')
    scorecard_file = get_latest_file('scorecard')
    issues_file = get_latest_file('issues')
    todos_file = get_latest_file('todos')
    vto_file = get_latest_file('vto')
    accountability_file = get_latest_file('accountability')
    
    data = {
        'timestamp': datetime.now().isoformat(),
        'rocks': {'rocks': [], 'summary': {}},
        'scorecard': {'metrics': [], 'summary': {}},
        'issues': {'issues': [], 'summary': {}},
        'todos': {'todos': [], 'summary': {}},
        'vto': {},
        'accountability': {'seats': [], 'summary': {}}
    }
    
    # Parse all data
    if rocks_file:
        data['rocks'] = parse_rocks(rocks_file)
    
    if scorecard_file:
        data['scorecard'] = parse_scorecard(scorecard_file)
    
    if issues_file:
        data['issues'] = parse_issues(issues_file)
    
    if todos_file:
        data['todos'] = parse_todos(todos_file)
    
    if vto_file:
        data['vto'] = parse_vto(vto_file)
    
    if accountability_file:
        data['accountability'] = parse_accountability_chart(accountability_file)
    
    return jsonify(data)

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Verify we can access data directory
        files_exist = os.path.exists(DATASHEETS_DIR)
        db_exists = DATABASE_PATH.exists()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'datasheets_accessible': files_exist,
            'database_accessible': db_exists
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 503

# =============================================================================
# EDITING API ENDPOINTS
# =============================================================================

def log_change(table_name, record_id, action, changed_by, changes, ip_address=None):
    """Log all changes to audit_log table"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    cursor.execute('''
        INSERT INTO audit_log (table_name, record_id, action, changed_by, changes, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (table_name, record_id, action, changed_by, json.dumps(changes), ip_address))
    
    conn.commit()
    conn.close()

@app.route('/api/rocks/<int:rock_id>', methods=['PUT'])
def update_rock_api(rock_id):
    """Update a rock field"""
    data = request.json
    field = data.get('field')
    value = data.get('value')
    changed_by = data.get('changed_by', 'System')
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get current value
        cursor.execute(f'SELECT {field} FROM rocks WHERE id = ?', (rock_id,))
        result = cursor.fetchone()
        old_value = result[0] if result else None
        
        # Update the field
        cursor.execute(f'''
            UPDATE rocks 
            SET {field} = ?, updated_at = ?, updated_by = ?
            WHERE id = ?
        ''', (value, datetime.now().isoformat(), changed_by, rock_id))
        
        # Log to history
        cursor.execute('''
            INSERT INTO rocks_history (rock_id, field_changed, old_value, new_value, changed_by)
            VALUES (?, ?, ?, ?, ?)
        ''', (rock_id, field, str(old_value), str(value), changed_by))
        
        conn.commit()
        conn.close()
        
        # Log to audit
        log_change('rocks', rock_id, 'UPDATE', changed_by, {
            'field': field,
            'old_value': old_value,
            'new_value': value
        })
        
        return jsonify({'success': True, 'message': 'Rock updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/rocks/<int:rock_id>/history', methods=['GET'])
def get_rock_history_api(rock_id):
    """Get rock change history"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
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
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/issues/<int:issue_id>/ids', methods=['POST'])
def ids_workflow_api(issue_id):
    """Move issue through IDS workflow"""
    data = request.json
    stage = data.get('stage')  # IDENTIFY, DISCUSS, or SOLVE
    changed_by = data.get('changed_by', 'System')
    notes = data.get('notes', '')
    solution = data.get('solution', '')
    
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        # Get current stage
        cursor.execute('SELECT ids_stage FROM issues WHERE id = ?', (issue_id,))
        result = cursor.fetchone()
        old_stage = result[0] if result else None
        
        updates = [stage, datetime.now().isoformat()]
        query = 'UPDATE issues SET ids_stage = ?, updated_at = ?'
        
        if notes:
            query += ', discussion_notes = ?'
            updates.append(notes)
        
        if solution:
            query += ', solution = ?'
            updates.append(solution)
        
        if stage == 'SOLVE':
            query += ', status = ?, resolved_at = ?'
            updates.extend(['RESOLVED', datetime.now().isoformat()])
        
        query += ' WHERE id = ?'
        updates.append(issue_id)
        
        cursor.execute(query, updates)
        
        # Log to history
        cursor.execute('''
            INSERT INTO issues_history (issue_id, field_changed, old_value, new_value, changed_by, change_note)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (issue_id, 'ids_stage', old_stage, stage, changed_by, notes))
        
        conn.commit()
        conn.close()
        
        # Log to audit
        log_change('issues', issue_id, 'IDS_WORKFLOW', changed_by, {
            'old_stage': old_stage,
            'new_stage': stage,
            'notes': notes,
            'solution': solution
        })
        
        return jsonify({'success': True, 'message': f'Issue moved to {stage} stage'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/issues/<int:issue_id>/history', methods=['GET'])
def get_issue_history_api(issue_id):
    """Get issue IDS workflow history"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
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
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/rocks/db', methods=['GET'])
def get_rocks_from_db():
    """Get all rocks from database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, description, owner, status, due_date, progress, quarter, updated_at, updated_by
            FROM rocks
            WHERE is_active = 1
            ORDER BY due_date
        ''')
        
        rocks = []
        for row in cursor.fetchall():
            rocks.append({
                'id': row[0],
                'description': row[1],
                'owner': row[2],
                'status': row[3],
                'due_date': row[4],
                'progress': row[5],
                'quarter': row[6],
                'updated_at': row[7],
                'updated_by': row[8]
            })
        
        conn.close()
        
        # Calculate summary
        total = len(rocks)
        complete = len([r for r in rocks if r['status'] == 'COMPLETE'])
        on_track = len([r for r in rocks if r['status'] in ['COMPLETE', 'ON TRACK']])
        at_risk = len([r for r in rocks if r['status'] in ['AT RISK', 'BLOCKED']])
        
        return jsonify({
            'success': True,
            'rocks': rocks,
            'summary': {
                'total': total,
                'complete': complete,
                'on_track': on_track,
                'at_risk': at_risk,
                'completion_pct': round((on_track / total * 100) if total > 0 else 0, 1)
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/issues/db', methods=['GET'])
def get_issues_from_db():
    """Get all issues from database"""
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, issue, priority, owner, date_added, status, ids_stage, discussion_notes, solution
            FROM issues
            WHERE is_active = 1
            ORDER BY 
                CASE priority 
                    WHEN 'HIGH' THEN 1 
                    WHEN 'MEDIUM' THEN 2 
                    WHEN 'LOW' THEN 3 
                END,
                date_added
        ''')
        
        issues = []
        for row in cursor.fetchall():
            issues.append({
                'id': row[0],
                'issue': row[1],
                'priority': row[2],
                'owner': row[3],
                'date_added': row[4],
                'status': row[5],
                'ids_stage': row[6],
                'discussion_notes': row[7],
                'solution': row[8]
            })
        
        conn.close()
        
        # Calculate summary
        high = len([i for i in issues if i['priority'] == 'HIGH'])
        
        return jsonify({
            'success': True,
            'issues': issues,
            'summary': {
                'total': len(issues),
                'high': high
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

if __name__ == '__main__':
    # Create archive directory if it doesn't exist
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # Run the app
    app.run(host='0.0.0.0', port=5002, debug=False)
