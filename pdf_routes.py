"""
PDF Generation Routes for EOS Platform
"""

from flask import session, send_file, abort
from datetime import datetime
from db_utils import get_db_connection
from auth import login_required, can_access_division
from pdf_generator import generate_vto_pdf, generate_l10_pdf


def register_pdf_routes(app):
    """Register PDF generation routes"""
    
    @app.route('/division/<int:division_id>/vto/pdf')
    @login_required
    def download_vto_pdf(division_id):
        """Generate and download VTO PDF"""
        # Check access
        user = session.get('user')
        if not can_access_division(user, division_id):
            abort(403)
        
        try:
            with get_db_connection() as db:
                pdf_buffer = generate_vto_pdf(division_id, db)
            
            # Get division name
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("SELECT name FROM divisions WHERE id = ?", (division_id,))
                division = cursor.fetchone()
                division_name = division[0] if division else f"Division_{division_id}"
            
            filename = f"VTO_{division_name}_{datetime.now().strftime('%Y%m%d')}.pdf"
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        except Exception as e:
            app.logger.error(f"Error generating VTO PDF: {e}")
            abort(500)
    
    @app.route('/division/<int:division_id>/l10/<int:meeting_id>/pdf')
    @login_required
    def download_l10_pdf(division_id, meeting_id):
        """Generate and download L10 Meeting PDF"""
        # Check access
        user = session.get('user')
        if not can_access_division(user, division_id):
            abort(403)
        
        try:
            with get_db_connection() as db:
                # Verify meeting belongs to this division
                cursor = db.cursor()
                cursor.execute(
                    "SELECT meeting_date FROM l10_meetings WHERE id = ? AND division_id = ?",
                    (meeting_id, division_id)
                )
                meeting = cursor.fetchone()
                
                if not meeting:
                    abort(404)
                
                pdf_buffer = generate_l10_pdf(meeting_id, db)
            
            # Get division name
            with get_db_connection() as db:
                cursor = db.cursor()
                cursor.execute("SELECT name FROM divisions WHERE id = ?", (division_id,))
                division = cursor.fetchone()
                division_name = division[0] if division else f"Division_{division_id}"
            
            meeting_date = meeting[0] if meeting else datetime.now().strftime('%Y%m%d')
            filename = f"L10_{division_name}_{meeting_date}.pdf"
            
            return send_file(
                pdf_buffer,
                mimetype='application/pdf',
                as_attachment=True,
                download_name=filename
            )
        except Exception as e:
            app.logger.error(f"Error generating L10 PDF: {e}")
            abort(500)
