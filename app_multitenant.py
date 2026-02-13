"""
EOS Platform - Multi-Tenant Version
Steensma Enterprises Strategic Dashboard with hierarchical organization support
"""

import os
from flask import Flask, session
from datetime import timedelta
from pathlib import Path

# Initialize Flask app
app = Flask(__name__)

# Secret key for sessions (CHANGE THIS IN PRODUCTION!)
app.secret_key = os.environ.get('SECRET_KEY', 'eos-platform-secret-key-change-this-in-production')

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=12)
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
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
register_pdf_routes(app)

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
    # Development mode only
    app.run(host='0.0.0.0', port=5002, debug=True)
