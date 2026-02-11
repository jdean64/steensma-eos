"""
EOS Platform - Multi-Tenant Authentication & Authorization
Role-Based Access Control (RBAC) with hierarchical permissions
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
from flask import session, redirect, url_for, flash, request
import bcrypt

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'

# =====================================================
# PASSWORD HASHING
# =====================================================

def hash_password(password: str) -> str:
    """Hash a password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash"""
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

# =====================================================
# SESSION TOKEN MANAGEMENT
# =====================================================

def generate_session_token() -> str:
    """Generate a secure random session token"""
    return secrets.token_urlsafe(32)

# =====================================================
# USER AUTHENTICATION
# =====================================================

def authenticate_user(username: str, password: str) -> dict:
    """
    Authenticate a user by username and password
    Returns user dict with roles and permissions, or None if auth fails
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get user
    cursor.execute("""
        SELECT id, username, email, full_name, password_hash, is_active
        FROM users
        WHERE username = ? AND is_active = 1
    """, (username,))
    
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return None
    
    # Verify password
    if not verify_password(password, user['password_hash']):
        conn.close()
        return None
    
    # Get user roles and permissions
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
    """, (user['id'],))
    
    roles = [dict(row) for row in cursor.fetchall()]
    
    # Update last login
    cursor.execute("""
        UPDATE users 
        SET last_login = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (user['id'],))
    
    conn.commit()
    conn.close()
    
    return {
        'id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'full_name': user['full_name'],
        'roles': roles,
        'is_parent_admin': any(r['role_name'] == 'PARENT_ADMIN' for r in roles)
    }

# =====================================================
# PERMISSION CHECKING
# =====================================================

def can_access_organization(user: dict, organization_id: int) -> bool:
    """Check if user can access an organization"""
    if user.get('is_parent_admin'):
        return True
    
    for role in user.get('roles', []):
        if role.get('organization_id') == organization_id:
            return True
    
    return False

def can_access_division(user: dict, division_id: int) -> bool:
    """Check if user can access a division"""
    if user.get('is_parent_admin'):
        return True
    
    for role in user.get('roles', []):
        if role.get('division_id') == division_id:
            return True
    
    return False

def can_edit_division(user: dict, division_id: int) -> bool:
    """Check if user can edit a division"""
    if user.get('is_parent_admin'):
        return True
    
    for role in user.get('roles', []):
        if role.get('division_id') == division_id:
            # Can edit if DIVISION_ADMIN or USER_RW
            if role.get('role_name') in ['DIVISION_ADMIN', 'USER_RW']:
                return True
    
    return False

def is_division_admin(user: dict, division_id: int) -> bool:
    """Check if user is admin of a specific division"""
    if user.get('is_parent_admin'):
        return True
    
    for role in user.get('roles', []):
        if role.get('division_id') == division_id and role.get('role_name') == 'DIVISION_ADMIN':
            return True
    
    return False

def get_user_divisions(user: dict) -> list:
    """Get list of divisions the user has access to"""
    if user.get('is_parent_admin'):
        # Parent admins see all divisions
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, organization_id, name, slug, full_slug, display_name
            FROM divisions
            WHERE is_active = 1
            ORDER BY name
        """)
        divisions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return divisions
    
    # Regular users see only their assigned divisions
    divisions = []
    seen_ids = set()
    
    for role in user.get('roles', []):
        div_id = role.get('division_id')
        if div_id and div_id not in seen_ids:
            divisions.append({
                'id': div_id,
                'organization_id': role.get('organization_id'),
                'name': role.get('division_name'),
                'slug': role.get('division_slug'),
                'full_slug': role.get('division_full_slug'),
                'display_name': role.get('division_name'),
                'role_name': role.get('role_name'),
                'can_edit': role.get('role_name') in ['DIVISION_ADMIN', 'USER_RW']
            })
            seen_ids.add(div_id)
    
    return divisions

# =====================================================
# FLASK DECORATORS FOR ROUTE PROTECTION
# =====================================================

def login_required(f):
    """Decorator to require login for a route"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def parent_admin_required(f):
    """Decorator to require parent admin privileges"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        user = session.get('user')
        if not user.get('is_parent_admin'):
            flash('Access denied. Parent administrator privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

def division_access_required(division_id_param='division_id'):
    """Decorator to require access to a specific division"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            user = session.get('user')
            division_id = kwargs.get(division_id_param) or request.args.get(division_id_param)
            
            if not division_id:
                flash('Division not specified.', 'danger')
                return redirect(url_for('dashboard'))
            
            division_id = int(division_id)
            
            if not can_access_division(user, division_id):
                flash('Access denied. You do not have permission to access this division.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def division_edit_required(division_id_param='division_id'):
    """Decorator to require edit permission for a specific division"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user' not in session:
                flash('Please log in to access this page.', 'warning')
                return redirect(url_for('login'))
            
            user = session.get('user')
            division_id = kwargs.get(division_id_param) or request.args.get(division_id_param)
            
            if not division_id:
                flash('Division not specified.', 'danger')
                return redirect(url_for('dashboard'))
            
            division_id = int(division_id)
            
            if not can_edit_division(user, division_id):
                flash('Access denied. You do not have edit permission for this division.', 'danger')
                return redirect(url_for('dashboard'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# =====================================================
# USER MANAGEMENT
# =====================================================

def create_user(username: str, email: str, password: str, full_name: str = None) -> int:
    """Create a new user"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    
    cursor.execute("""
        INSERT INTO users (username, email, password_hash, full_name)
        VALUES (?, ?, ?, ?)
    """, (username, email, password_hash, full_name))
    
    user_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return user_id

def assign_role(user_id: int, role_name: str, organization_id: int = None, 
                division_id: int = None, assigned_by: int = None) -> int:
    """Assign a role to a user"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get role ID
    cursor.execute("SELECT id FROM roles WHERE name = ?", (role_name,))
    role = cursor.fetchone()
    
    if not role:
        conn.close()
        raise ValueError(f"Role '{role_name}' not found")
    
    role_id = role[0]
    
    # Assign role
    cursor.execute("""
        INSERT INTO user_roles (user_id, role_id, organization_id, division_id, assigned_by)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, role_id, organization_id, division_id, assigned_by))
    
    assignment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return assignment_id

def get_user_by_id(user_id: int) -> dict:
    """Get user by ID with roles"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, email, full_name, is_active
        FROM users
        WHERE id = ?
    """, (user_id,))
    
    user = cursor.fetchone()
    
    if not user:
        conn.close()
        return None
    
    # Get roles
    cursor.execute("""
        SELECT 
            r.name as role_name,
            r.display_name as role_display,
            ur.organization_id,
            ur.division_id,
            o.name as org_name,
            d.name as division_name
        FROM user_roles ur
        JOIN roles r ON ur.role_id = r.id
        LEFT JOIN organizations o ON ur.organization_id = o.id
        LEFT JOIN divisions d ON ur.division_id = d.id
        WHERE ur.user_id = ? AND ur.is_active = 1
    """, (user_id,))
    
    roles = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return {
        'id': user['id'],
        'username': user['username'],
        'email': user['email'],
        'full_name': user['full_name'],
        'is_active': user['is_active'],
        'roles': roles,
        'is_parent_admin': any(r['role_name'] == 'PARENT_ADMIN' for r in roles)
    }

# =====================================================
# DIVISION MANAGEMENT
# =====================================================

def create_division(organization_id: int, name: str, slug: str, 
                   display_name: str = None, created_by: int = None) -> int:
    """Create a new division"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    # Get organization slug
    cursor.execute("SELECT slug FROM organizations WHERE id = ?", (organization_id,))
    org = cursor.fetchone()
    
    if not org:
        conn.close()
        raise ValueError(f"Organization {organization_id} not found")
    
    org_slug = org[0]
    full_slug = f"{org_slug}.{slug}"
    
    if not display_name:
        display_name = name
    
    cursor.execute("""
        INSERT INTO divisions (organization_id, name, slug, full_slug, display_name, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (organization_id, name, slug, full_slug, display_name, created_by))
    
    division_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return division_id

def get_division_by_id(division_id: int) -> dict:
    """Get division by ID"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT d.*, o.name as org_name, o.slug as org_slug
        FROM divisions d
        JOIN organizations o ON d.organization_id = o.id
        WHERE d.id = ?
    """, (division_id,))
    
    division = cursor.fetchone()
    conn.close()
    
    return dict(division) if division else None

def get_all_divisions(organization_id: int = None) -> list:
    """Get all divisions, optionally filtered by organization"""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if organization_id:
        cursor.execute("""
            SELECT * FROM divisions
            WHERE organization_id = ? AND is_active = 1
            ORDER BY name
        """, (organization_id,))
    else:
        cursor.execute("""
            SELECT * FROM divisions
            WHERE is_active = 1
            ORDER BY name
        """)
    
    divisions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    
    return divisions

# =====================================================
# AUDIT LOGGING
# =====================================================

def log_action(user_id: int, table_name: str, record_id: int, action: str,
               changes: dict = None, organization_id: int = None, 
               division_id: int = None, ip_address: str = None):
    """Log an action to the audit trail"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()
    
    import json
    changes_json = json.dumps(changes) if changes else None
    
    cursor.execute("""
        INSERT INTO audit_log (
            organization_id, division_id, user_id, table_name, 
            record_id, action, changes, ip_address
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (organization_id, division_id, user_id, table_name, 
          record_id, action, changes_json, ip_address))
    
    conn.commit()
    conn.close()
