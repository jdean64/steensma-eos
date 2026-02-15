"""
EOS Platform - Flask Routes for Multi-Tenant System
Login, Dashboard, Division Selection, and Authentication
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from auth import (
    authenticate_user, login_required, parent_admin_required,
    division_access_required, division_edit_required,
    get_user_divisions, can_edit_division, can_access_division,
    create_division, log_action, is_saml_enabled, get_authentication_methods
)
import sqlite3
from pathlib import Path
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

def get_db():
    """Get database connection with timeout for concurrent access"""
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

# =====================================================
# AUTHENTICATION ROUTES
# =====================================================

def register_auth_routes(app):
    """Register authentication and navigation routes"""
    
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Login page"""
        # Get available authentication methods
        auth_methods = get_authentication_methods()
        
        if request.method == 'POST':
            username = request.form.get('username')
            password = request.form.get('password')
            
            user = authenticate_user(username, password)
            
            if user:
                session['user'] = user
                session['auth_method'] = 'password'
                session.permanent = True
                
                # Log login
                log_action(
                    user['id'], 'users', user['id'], 'LOGIN',
                    ip_address=request.remote_addr
                )
                
                flash(f"Welcome, {user['full_name'] or user['username']}!", 'success')
                
                # Redirect to next page or dashboard
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for('dashboard'))
            else:
                flash('Invalid username or password', 'danger')
        
        return render_template('login.html', auth_methods=auth_methods)
    
    @app.route('/logout')
    def logout():
        """Logout - handles both password and SAML sessions"""
        if 'user' in session:
            user = session['user']
            auth_method = session.get('auth_method', 'password')
            
            log_action(
                user['id'], 'users', user['id'], 'LOGOUT',
                changes={'auth_method': auth_method},
                ip_address=request.remote_addr
            )
            
            # If user authenticated via SAML, redirect to SAML logout
            if auth_method == 'saml' and is_saml_enabled():
                return redirect(url_for('saml_logout_route'))
        
        session.clear()
        flash('You have been logged out', 'info')
        return redirect(url_for('login'))

# =====================================================
# DASHBOARD & NAVIGATION ROUTES
# =====================================================

def register_dashboard_routes(app):
    """Register dashboard and division selection routes"""
    
    @app.route('/')
    @login_required
    def dashboard():
        """
        Main landing dashboard
        Parent admins: See all divisions
        Division users: See their assigned divisions
        """
        user = session.get('user')
        divisions = get_user_divisions(user)
        
        # If user has access to only one division, go directly to it
        if len(divisions) == 1 and not user.get('is_parent_admin'):
            return redirect(url_for('division_dashboard', division_id=divisions[0]['id']))
        
        # Otherwise show division selector
        conn = get_db()
        cursor = conn.cursor()
        
        # Get organization info
        cursor.execute("SELECT * FROM organizations WHERE id = 1")
        organization = dict(cursor.fetchone())
        
        # Enrich division data with metrics
        for division in divisions:
            # Get active rocks count
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM rocks 
                WHERE division_id = ? AND is_active = 1
            """, (division['id'],))
            division['rocks_count'] = cursor.fetchone()['count']
            
            # Get open issues count
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM issues 
                WHERE division_id = ? AND status = 'OPEN' AND is_active = 1
            """, (division['id'],))
            division['issues_count'] = cursor.fetchone()['count']
            
            # Get pending todos count
            cursor.execute("""
                SELECT COUNT(*) as count 
                FROM todos 
                WHERE division_id = ? AND status IN ('OPEN', 'IN PROGRESS') AND is_active = 1
            """, (division['id'],))
            division['todos_count'] = cursor.fetchone()['count']
        
        # Corporate summary for parent admins
        corporate_summary = None
        if user.get('is_parent_admin'):
            cursor.execute("SELECT COUNT(*) as count FROM vto WHERE division_id IS NULL AND is_active = 1")
            corp_vto = cursor.fetchone()['count'] > 0
            cursor.execute("SELECT COUNT(*) as count FROM accountability_chart WHERE division_id IS NULL AND is_active = 1")
            corp_seats = cursor.fetchone()['count']
            corporate_summary = {'vto_exists': corp_vto, 'seats': corp_seats}

        conn.close()

        return render_template('parent_dashboard.html',
                             user=user,
                             organization=organization,
                             divisions=divisions,
                             corporate_summary=corporate_summary)
    
    @app.route('/division/<int:division_id>')
    @login_required
    @division_access_required('division_id')
    def division_dashboard(division_id):
        """
        Division-specific EOS dashboard (6-card view)
        Shows: Rocks, Scorecard, Issues, To-Dos, Vision, Accountability
        """
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
        
        # Get summary metrics for each card
        
        # ROCKS
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'COMPLETE' THEN 1 ELSE 0 END) as complete,
                SUM(CASE WHEN status IN ('ON TRACK', 'COMPLETE') THEN 1 ELSE 0 END) as on_track
            FROM rocks
            WHERE division_id = ? AND is_active = 1
        """, (division_id,))
        rocks_summary = dict(cursor.fetchone())
        
        # SCORECARD
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'GREEN' THEN 1 ELSE 0 END) as green,
                SUM(CASE WHEN status = 'YELLOW' THEN 1 ELSE 0 END) as yellow,
                SUM(CASE WHEN status = 'RED' THEN 1 ELSE 0 END) as red
            FROM scorecard_metrics
            WHERE division_id = ? AND is_active = 1
        """, (division_id,))
        scorecard_summary = dict(cursor.fetchone())
        
        # ISSUES
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN priority = 'HIGH' THEN 1 ELSE 0 END) as high,
                SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open
            FROM issues
            WHERE division_id = ? AND is_active = 1
        """, (division_id,))
        issues_summary = dict(cursor.fetchone())
        
        # TODOS
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'OPEN' THEN 1 ELSE 0 END) as open,
                SUM(CASE WHEN status = 'COMPLETE' THEN 1 ELSE 0 END) as complete
            FROM todos
            WHERE division_id = ? AND is_active = 1
        """, (division_id,))
        todos_summary = dict(cursor.fetchone())
        
        # VTO (check if exists)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM vto
            WHERE division_id = ? AND is_active = 1
        """, (division_id,))
        vto_exists = cursor.fetchone()['count'] > 0
        
        # ACCOUNTABILITY (check if exists)
        cursor.execute("""
            SELECT COUNT(*) as count
            FROM accountability_chart
            WHERE division_id = ? AND is_active = 1
        """, (division_id,))
        accountability_count = cursor.fetchone()['count']
        
        # L10 MEETINGS
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status IN ('SCHEDULED', 'IN_PROGRESS') THEN 1 ELSE 0 END) as upcoming,
                AVG(CAST(actual_duration_minutes AS FLOAT)) as avg_duration
            FROM l10_meetings
            WHERE division_id = ?
        """, (division_id,))
        l10_summary = dict(cursor.fetchone())
        
        conn.close()
        
        # Check if user can edit
        can_edit = can_edit_division(user, division_id)
        
        return render_template('division_dashboard.html',
                             user=user,
                             division=division,
                             can_edit=can_edit,
                             rocks_summary=rocks_summary,
                             scorecard_summary=scorecard_summary,
                             issues_summary=issues_summary,
                             todos_summary=todos_summary,
                             vto_exists=vto_exists,
                             accountability_count=accountability_count,
                             l10_summary=l10_summary)

# =====================================================
# PARENT ADMIN ROUTES
# =====================================================

def register_admin_routes(app):
    """Register parent admin routes"""
    
    @app.route('/admin/create-division', methods=['GET', 'POST'])
    @parent_admin_required
    def admin_create_division():
        """Create a new division (parent admins only)"""
        user = session.get('user')
        
        if request.method == 'POST':
            name = request.form.get('name')
            slug = request.form.get('slug').lower().replace(' ', '-')
            display_name = request.form.get('display_name') or name
            
            try:
                division_id = create_division(
                    organization_id=1,  # Steensma
                    name=name,
                    slug=slug,
                    display_name=display_name,
                    created_by=user['id']
                )
                
                log_action(
                    user['id'], 'divisions', division_id, 'CREATE',
                    changes={'name': name, 'slug': slug},
                    organization_id=1,
                    ip_address=request.remote_addr
                )
                
                flash(f"Division '{name}' created successfully!", 'success')
                return redirect(url_for('dashboard'))
            
            except Exception as e:
                flash(f"Error creating division: {str(e)}", 'danger')
        
        return render_template('admin_create_division.html', user=user)
    
    @app.route('/admin/users')
    @parent_admin_required
    def admin_users():
        """Manage users (parent admins only)"""
        user = session.get('user')
        
        conn = get_db()
        cursor = conn.cursor()
        
        # Get all users with their roles
        cursor.execute("""
            SELECT DISTINCT u.*
            FROM users u
            ORDER BY u.full_name, u.username
        """)
        users = [dict(row) for row in cursor.fetchall()]
        
        # Get roles for each user
        for u in users:
            cursor.execute("""
                SELECT 
                    r.display_name as role,
                    d.name as division,
                    ur.is_active
                FROM user_roles ur
                JOIN roles r ON ur.role_id = r.id
                LEFT JOIN divisions d ON ur.division_id = d.id
                WHERE ur.user_id = ?
                ORDER BY r.level, d.name
            """, (u['id'],))
            u['roles'] = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('admin_users.html', user=user, users=users)

# =====================================================
# API ROUTES
# =====================================================

def register_api_routes(app):
    """Register API endpoints"""
    
    @app.route('/api/division/<int:division_id>/summary')
    @login_required
    @division_access_required('division_id')
    def api_division_summary(division_id):
        """Get division summary metrics (JSON)"""
        conn = get_db()
        cursor = conn.cursor()
        
        summary = {}
        
        # Rocks
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM rocks
            WHERE division_id = ? AND is_active = 1
            GROUP BY status
        """, (division_id,))
        summary['rocks'] = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Issues
        cursor.execute("""
            SELECT priority, COUNT(*) as count
            FROM issues
            WHERE division_id = ? AND is_active = 1
            GROUP BY priority
        """, (division_id,))
        summary['issues'] = {row['priority']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return jsonify(summary)
