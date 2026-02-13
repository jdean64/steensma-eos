"""
AWS IAM Identity Center SAML 2.0 Authentication Module
Integrates with Identity Center for Single Sign-On
"""

import os
import json
from pathlib import Path
from urllib.parse import urlparse
from flask import request, session, redirect, url_for, make_response
from onelogin.saml2.auth import OneLogin_Saml2_Auth
from onelogin.saml2.utils import OneLogin_Saml2_Utils
from onelogin.saml2.errors import OneLogin_Saml2_Error
import sqlite3
from datetime import datetime

DATABASE_PATH = Path(__file__).parent / 'eos_data.db'
SAML_SETTINGS_FILE = Path(__file__).parent / 'saml_settings.json'

# =====================================================
# SAML CONFIGURATION LOADER
# =====================================================

def load_saml_settings():
    """Load SAML settings from configuration file"""
    if not SAML_SETTINGS_FILE.exists():
        raise FileNotFoundError(
            f"SAML settings file not found: {SAML_SETTINGS_FILE}\n"
            "Run: python configure_saml.py to create it."
        )
    
    with open(SAML_SETTINGS_FILE, 'r') as f:
        return json.load(f)

# =====================================================
# SAML REQUEST PREPARATION
# =====================================================

def prepare_flask_request(request_obj):
    """
    Prepare Flask request object for OneLogin SAML library
    Converts Flask request to format expected by python3-saml
    """
    url_data = urlparse(request_obj.url)
    
    return {
        'https': 'on' if request_obj.scheme == 'https' else 'off',
        'http_host': request_obj.host,
        'server_port': url_data.port or (443 if request_obj.scheme == 'https' else 80),
        'script_name': request_obj.path,
        'get_data': request_obj.args.copy(),
        'post_data': request_obj.form.copy(),
        'query_string': request_obj.query_string.decode('utf-8')
    }

# =====================================================
# SAML AUTHENTICATION
# =====================================================

def init_saml_auth(req):
    """Initialize SAML authentication object"""
    saml_settings = load_saml_settings()
    auth = OneLogin_Saml2_Auth(req, saml_settings)
    return auth

def saml_login(return_to=None):
    """
    Initiate SAML login flow
    Redirects user to AWS IAM Identity Center login page
    
    Args:
        return_to: Optional URL to return to after successful login
    
    Returns:
        Flask redirect response to Identity Center
    """
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    # Store return URL in session
    if return_to:
        session['saml_return_to'] = return_to
    
    # Generate SAML login request and redirect
    sso_built_url = auth.login()
    session['AuthNRequestID'] = auth.get_last_request_id()
    
    return redirect(sso_built_url)

def saml_acs():
    """
    Assertion Consumer Service - handles SAML response from Identity Center
    This is where users land after successful authentication
    
    Returns:
        Flask redirect response or error response
    """
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    request_id = session.pop('AuthNRequestID', None)
    
    # Process SAML response
    auth.process_response(request_id=request_id)
    
    errors = auth.get_errors()
    
    if errors:
        error_reason = auth.get_last_error_reason()
        return make_response(
            f"SAML Authentication Error: {', '.join(errors)}\n"
            f"Reason: {error_reason}", 
            401
        )
    
    # Check if authentication was successful
    if not auth.is_authenticated():
        return make_response("Authentication failed - not authenticated", 401)
    
    # Get user attributes from SAML assertion
    attributes = auth.get_attributes()
    nameid = auth.get_nameid()
    session_index = auth.get_session_index()
    
    # Extract user information
    user_info = {
        'email': nameid,  # Usually email address
        'first_name': attributes.get('firstName', [''])[0] if 'firstName' in attributes else '',
        'last_name': attributes.get('lastName', [''])[0] if 'lastName' in attributes else '',
        'full_name': f"{attributes.get('firstName', [''])[0]} {attributes.get('lastName', [''])[0]}".strip(),
        'groups': attributes.get('groups', []),
        'session_index': session_index
    }
    
    # Get or create user in database
    user = get_or_create_sso_user(user_info)
    
    if not user:
        return make_response("Failed to create or retrieve user", 500)
    
    # Map SSO groups to EOS roles
    eos_roles = map_sso_groups_to_roles(user_info['groups'], user['id'])
    
    # Create Flask session
    session['user_id'] = user['id']
    session['username'] = user['username']
    session['email'] = user['email']
    session['full_name'] = user['full_name']
    session['roles'] = eos_roles
    session['auth_method'] = 'saml'
    session['saml_session_index'] = session_index
    session['saml_nameid'] = nameid
    
    # Get return URL or default to dashboard
    return_to = session.pop('saml_return_to', url_for('home'))
    
    return redirect(return_to)

def saml_logout():
    """
    Initiate SAML logout (Single Logout)
    Logs user out locally and at Identity Center
    
    Returns:
        Flask redirect response
    """
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    name_id = session.get('saml_nameid')
    session_index = session.get('saml_session_index')
    
    # Clear local session
    session.clear()
    
    # If we have SAML session info, do SLO
    if name_id and session_index:
        return redirect(auth.logout(name_id=name_id, session_index=session_index))
    
    # Otherwise just redirect to home
    return redirect(url_for('home'))

def saml_metadata():
    """
    Generate SAML Service Provider metadata
    AWS Identity Center needs this to configure the application
    
    Returns:
        XML metadata document
    """
    req = prepare_flask_request(request)
    auth = init_saml_auth(req)
    
    settings = auth.get_settings()
    metadata = settings.get_sp_metadata()
    errors = settings.validate_metadata(metadata)
    
    if errors:
        return make_response(f"Metadata validation error: {', '.join(errors)}", 500)
    
    resp = make_response(metadata)
    resp.headers['Content-Type'] = 'text/xml'
    return resp

# =====================================================
# USER MANAGEMENT
# =====================================================

def get_or_create_sso_user(user_info):
    """
    Get existing user or create new user from SSO information
    
    Args:
        user_info: Dict with email, first_name, last_name, full_name
    
    Returns:
        User dict or None
    """
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        # Try to find existing user by email
        cursor.execute("""
            SELECT id, username, email, full_name, is_active, sso_identity, sso_provider
            FROM users
            WHERE email = ? OR sso_identity = ?
        """, (user_info['email'], user_info['email']))
        
        user = cursor.fetchone()
        
        if user:
            # Update last login and SSO info
            cursor.execute("""
                UPDATE users
                SET last_login = CURRENT_TIMESTAMP,
                    sso_identity = ?,
                    sso_provider = 'aws_sso',
                    full_name = ?
                WHERE id = ?
            """, (user_info['email'], user_info['full_name'], user['id']))
            conn.commit()
            
            return dict(user)
        
        # Create new user
        username = user_info['email'].split('@')[0]  # Use email prefix as username
        
        cursor.execute("""
            INSERT INTO users (
                username, email, full_name, 
                sso_identity, sso_provider, 
                is_active, created_at, last_login
            ) VALUES (?, ?, ?, ?, 'aws_sso', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """, (username, user_info['email'], user_info['full_name'], user_info['email']))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # Return new user
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        return dict(cursor.fetchone())
        
    except Exception as e:
        conn.rollback()
        print(f"Error in get_or_create_sso_user: {e}")
        return None
    finally:
        conn.close()

def map_sso_groups_to_roles(sso_groups, user_id):
    """
    Map AWS SSO groups to EOS platform roles
    
    AWS SSO Group → EOS Role Mapping:
    - Steensma-Admins → platform_admin
    - Steensma-Managers → org_admin
    - Steensma-Users → user
    - Steensma-ReadOnly → viewer
    
    Args:
        sso_groups: List of AWS SSO group names
        user_id: User ID to assign roles to
    
    Returns:
        List of role dicts
    """
    # Group to role mapping
    group_role_map = {
        'Steensma-Admins': 'platform_admin',
        'Steensma-Managers': 'org_admin',
        'Steensma-Users': 'user',
        'Steensma-ReadOnly': 'viewer'
    }
    
    conn = sqlite3.connect(DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    roles = []
    
    try:
        for group_name in sso_groups:
            role_name = group_role_map.get(group_name)
            
            if not role_name:
                continue  # Skip unmapped groups
            
            # Get role ID
            cursor.execute("SELECT id, name, display_name, level FROM roles WHERE name = ?", (role_name,))
            role = cursor.fetchone()
            
            if not role:
                continue
            
            # Check if user already has this role
            cursor.execute("""
                SELECT id FROM user_roles 
                WHERE user_id = ? AND role_id = ? AND is_active = 1
            """, (user_id, role['id']))
            
            existing = cursor.fetchone()
            
            if not existing:
                # Assign role to user (platform level - no specific org/division)
                cursor.execute("""
                    INSERT INTO user_roles (user_id, role_id, organization_id, division_id, is_active)
                    VALUES (?, ?, NULL, NULL, 1)
                """, (user_id, role['id']))
            
            roles.append({
                'role_name': role['name'],
                'role_display': role['display_name'],
                'role_level': role['level']
            })
        
        conn.commit()
        
    except Exception as e:
        conn.rollback()
        print(f"Error in map_sso_groups_to_roles: {e}")
    finally:
        conn.close()
    
    return roles

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def is_saml_enabled():
    """Check if SAML authentication is properly configured"""
    return SAML_SETTINGS_FILE.exists()

def get_sso_portal_url():
    """Get the AWS SSO portal URL from settings"""
    try:
        settings = load_saml_settings()
        return settings.get('idp', {}).get('singleSignOnService', {}).get('url', '')
    except:
        return ''
