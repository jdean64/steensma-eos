"""
EOS Platform - SAML 2.0 Routes
Handles AWS IAM Identity Center SSO integration
"""

from flask import Blueprint, request, session, redirect, url_for, flash, render_template
from auth import log_action, is_saml_enabled
from saml_auth import saml_login, saml_acs, saml_logout, saml_metadata
from onelogin.saml2.errors import OneLogin_Saml2_Error

def register_saml_routes(app):
    """Register SAML authentication routes"""
    
    @app.route('/saml/login')
    def saml_login_route():
        """
        Initiate SAML login flow
        Redirects to AWS IAM Identity Center
        """
        if not is_saml_enabled():
            flash('SAML authentication is not configured on this server', 'danger')
            return redirect(url_for('login'))
        
        try:
            # Get return URL from query param
            return_to = request.args.get('next') or url_for('dashboard')
            return saml_login(return_to=return_to)
        except OneLogin_Saml2_Error as e:
            flash(f'SAML Error: {str(e)}', 'danger')
            return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f"SAML login error: {e}")
            flash('An error occurred during SSO login. Please try password login or contact IT.', 'danger')
            return redirect(url_for('login'))
    
    @app.route('/saml/acs', methods=['POST'])
    def saml_acs_route():
        """
        SAML Assertion Consumer Service
        AWS Identity Center redirects here after successful authentication
        """
        if not is_saml_enabled():
            flash('SAML authentication is not configured', 'danger')
            return redirect(url_for('login'))
        
        try:
            response = saml_acs()
            
            # Log successful SSO login
            if 'user_id' in session:
                log_action(
                    session['user_id'], 
                    'users', 
                    session['user_id'], 
                    'SSO_LOGIN',
                    changes={'auth_method': 'saml', 'provider': 'aws_sso'},
                    ip_address=request.remote_addr
                )
            
            return response
            
        except OneLogin_Saml2_Error as e:
            app.logger.error(f"SAML ACS error: {e}")
            flash(f'SAML Authentication Error: {str(e)}', 'danger')
            return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f"SAML ACS unexpected error: {e}")
            flash('Authentication failed. Please try again or use password login.', 'danger')
            return redirect(url_for('login'))
    
    @app.route('/saml/logout')
    def saml_logout_route():
        """
        SAML Single Logout
        Logs out both locally and at Identity Center
        """
        if not is_saml_enabled():
            session.clear()
            return redirect(url_for('login'))
        
        try:
            # Log logout action before clearing session
            if 'user_id' in session:
                log_action(
                    session['user_id'],
                    'users',
                    session['user_id'],
                    'SSO_LOGOUT',
                    ip_address=request.remote_addr
                )
            
            return saml_logout()
        except Exception as e:
            app.logger.error(f"SAML logout error: {e}")
            session.clear()
            return redirect(url_for('login'))
    
    @app.route('/saml/sls')
    def saml_sls_route():
        """
        SAML Single Logout Service
        Receives logout requests from Identity Center
        """
        session.clear()
        flash('You have been logged out', 'info')
        return redirect(url_for('login'))
    
    @app.route('/saml/metadata')
    def saml_metadata_route():
        """
        SAML Service Provider Metadata
        AWS Identity Center uses this to configure the application
        """
        if not is_saml_enabled():
            return "SAML not configured", 404
        
        try:
            return saml_metadata()
        except Exception as e:
            app.logger.error(f"SAML metadata error: {e}")
            return f"Error generating metadata: {str(e)}", 500
    
    @app.route('/saml/test')
    def saml_test_route():
        """
        Test endpoint to check SAML configuration
        Only works in debug/dev mode
        """
        if not app.debug:
            return "Not available in production", 403
        
        config_status = {
            'saml_enabled': is_saml_enabled(),
            'session_data': {k: str(v)[:100] for k, v in session.items() if not k.startswith('_')},
            'config_file_exists': (app.root_path + '/saml_settings.json') if is_saml_enabled() else 'No'
        }
        
        return render_template('saml_test.html', config=config_status) if app.debug else {}
