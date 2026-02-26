"""
EOS Platform - Multi-Tenant Version
Steensma Enterprises Strategic Dashboard with hierarchical organization support
"""

import os
from flask import Flask, session, request
from datetime import timedelta
from pathlib import Path

# Initialize Flask app
app = Flask(__name__)

# Secret key for sessions
app.secret_key = os.environ.get('SECRET_KEY', 'e7254a50fc2634e2b103f222034d16ca04a5a4ea6a41bc81fabe603678f3d49e')

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Database configuration
DATABASE_PATH = Path(__file__).parent / 'eos_data.db'
app.config['DATABASE_PATH'] = DATABASE_PATH

# Import and register routes
from routes import (
    register_auth_routes,
    register_dashboard_routes,
    register_admin_routes,
    register_api_routes
)
from issues_routes import register_issues_routes
from l10_routes import register_l10_routes
from rocks_routes import register_rocks_routes
from scorecard_routes import register_scorecard_routes
from todos_routes import register_todos_routes
from vision_routes import register_vision_routes
from accountability_routes import register_accountability_routes
from corporate_routes import register_corporate_routes
from pdf_routes import register_pdf_routes
from saml_routes import register_saml_routes

register_auth_routes(app)
register_saml_routes(app)  # AWS IAM Identity Center SSO
register_dashboard_routes(app)
register_admin_routes(app)
register_api_routes(app)
register_issues_routes(app)
register_l10_routes(app)
register_rocks_routes(app)
register_scorecard_routes(app)
register_todos_routes(app)
register_vision_routes(app)
register_accountability_routes(app)
register_corporate_routes(app)
register_pdf_routes(app)

# =====================================================
# AWS SSO Auto-Login via oauth2-proxy headers
# =====================================================
@app.before_request
def auto_login_from_sso():
    """
    Auto-login EOS users based on X-Auth-Email header from oauth2-proxy.
    If user is already logged in (session exists), skip.
    If X-Auth-Email is present, look up the EOS user by email and auto-login.
    """
    # Skip if already logged in
    if 'user' in session:
        return
    
    # Skip for static files and login/logout routes
    if request.path.startswith('/static') or request.path in ('/login', '/logout'):
        return
    
    auth_email = request.headers.get('X-Auth-Email')
    if not auth_email:
        return
    
    # Look up user by email
    from auth import _get_db
    conn = _get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT id, username, email, full_name
            FROM users WHERE email = ? AND is_active = 1
        """, (auth_email,))
        user_row = cursor.fetchone()
        
        if not user_row:
            return  # No matching EOS user, fall through to normal login
        
        # Get roles
        cursor.execute("""
            SELECT
                ur.id as assignment_id,
                r.name as role_name,
                r.display_name as role_display,
                r.level as role_level,
                ur.organization_id,
                ur.division_id,
                o.name as org_name,
                o.slug as org_slug,
                d.name as division_name,
                d.slug as division_slug,
                d.full_slug as division_full_slug
            FROM user_roles ur
            JOIN roles r ON ur.role_id = r.id
            LEFT JOIN organizations o ON ur.organization_id = o.id
            LEFT JOIN divisions d ON ur.division_id = d.id
            WHERE ur.user_id = ? AND ur.is_active = 1
        """, (user_row['id'],))
        roles = [dict(row) for row in cursor.fetchall()]
        
        # Update last login
        cursor.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?",
                       (user_row['id'],))
        conn.commit()
        
        # Set session (same structure as authenticate_user)
        session['user'] = {
            'id': user_row['id'],
            'username': user_row['username'],
            'email': user_row['email'],
            'full_name': user_row['full_name'],
            'roles': roles,
            'is_parent_admin': any(r['role_name'] == 'PARENT_ADMIN' for r in roles)
        }
        session['auth_method'] = 'aws_sso'
        session.permanent = True
    finally:
        conn.close()

# Template context processor to make datetime available
@app.context_processor
def inject_now():
    """Make 'now' function available in templates"""
    from datetime import datetime
    return {'now':datetime.now}

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return '<h1>404 - Page Not Found</h1>', 404

@app.errorhandler(500)
def internal_error(e):
    return '<h1>500 - Internal Server Error</h1>', 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5002, debug=False)
