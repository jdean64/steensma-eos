"""
EOS Platform - Email Service
Sends task assignment notifications to owners and their leads.
Configure via environment variables:
  EOS_SMTP_HOST - SMTP server hostname
  EOS_SMTP_PORT - SMTP port (default: 587)
  EOS_SMTP_USER - SMTP username
  EOS_SMTP_PASS - SMTP password
  EOS_SMTP_FROM - From email address
  EOS_SMTP_TLS  - Use TLS (default: true)
"""

import os
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

logger = logging.getLogger(__name__)

# SMTP configuration from environment
SMTP_CONFIG = {
    'host': os.environ.get('EOS_SMTP_HOST', ''),
    'port': int(os.environ.get('EOS_SMTP_PORT', '587')),
    'user': os.environ.get('EOS_SMTP_USER', ''),
    'password': os.environ.get('EOS_SMTP_PASS', ''),
    'from_email': os.environ.get('EOS_SMTP_FROM', 'eos@coresteensma.com'),
    'use_tls': os.environ.get('EOS_SMTP_TLS', 'true').lower() == 'true',
}


def is_email_configured():
    """Check if SMTP is configured"""
    return bool(SMTP_CONFIG['host'] and SMTP_CONFIG['user'])


def send_email(to_email, subject, html_body, text_body=None):
    """Send an email via SMTP. Returns (success, error_message)."""
    if not is_email_configured():
        logger.warning("Email not configured - skipping send to %s", to_email)
        return False, "Email not configured. Set EOS_SMTP_HOST and EOS_SMTP_USER environment variables."

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = SMTP_CONFIG['from_email']
        msg['To'] = to_email

        if text_body:
            msg.attach(MIMEText(text_body, 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port'], timeout=10) as server:
            if SMTP_CONFIG['use_tls']:
                server.starttls()
            server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
            server.send_message(msg)

        logger.info("Email sent to %s: %s", to_email, subject)
        return True, None

    except Exception as e:
        logger.error("Failed to send email to %s: %s", to_email, str(e))
        return False, str(e)


def build_task_email_html(tasks, recipient_name, division_name):
    """Build HTML email body for task assignment notification"""
    task_rows = ""
    for t in tasks:
        priority_color = {'HIGH': '#dc3545', 'MEDIUM': '#ffc107', 'LOW': '#28a745'}.get(
            t.get('priority', 'MEDIUM'), '#6c757d')
        due = t.get('due_date', 'No due date') or 'No due date'
        source = t.get('source', '')
        task_rows += f"""
        <tr>
            <td style="padding: 12px 16px; border-bottom: 1px solid #f0f0f0; font-size: 14px;">
                {t.get('task', t.get('todo', ''))}
            </td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #f0f0f0; font-size: 13px; color: #6a6a6a;">
                {due}
            </td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #f0f0f0;">
                <span style="display: inline-block; padding: 2px 10px; border-radius: 10px;
                       font-size: 11px; font-weight: 600; color: white; background: {priority_color};">
                    {t.get('priority', 'MEDIUM')}
                </span>
            </td>
            <td style="padding: 12px 16px; border-bottom: 1px solid #f0f0f0; font-size: 12px; color: #999;">
                {source}
            </td>
        </tr>"""

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                 background: #f5f5f5; margin: 0; padding: 0;">
        <div style="max-width: 640px; margin: 0 auto; background: white;">
            <!-- Header -->
            <div style="background: #1a1a1a; padding: 24px 32px;">
                <h1 style="color: white; font-size: 20px; margin: 0; font-weight: 600;">
                    EOS Platform - Task Assignment
                </h1>
                <p style="color: #b0b0b0; font-size: 13px; margin: 4px 0 0 0;">
                    {division_name}
                </p>
            </div>

            <!-- Body -->
            <div style="padding: 32px;">
                <p style="font-size: 15px; color: #2a2a2a; margin: 0 0 8px 0;">
                    Hello {recipient_name},
                </p>
                <p style="font-size: 14px; color: #4a4a4a; margin: 0 0 24px 0;">
                    You have <strong>{len(tasks)}</strong> assigned task{'s' if len(tasks) != 1 else ''}
                    in the {division_name} division.
                </p>

                <!-- Tasks Table -->
                <table style="width: 100%; border-collapse: collapse; border: 1px solid #e5e5e5;
                              border-radius: 6px; overflow: hidden;">
                    <thead>
                        <tr style="background: #f8f9fa;">
                            <th style="padding: 10px 16px; text-align: left; font-size: 11px;
                                       color: #6a6a6a; text-transform: uppercase; letter-spacing: 0.05em;
                                       border-bottom: 2px solid #e5e5e5;">Task</th>
                            <th style="padding: 10px 16px; text-align: left; font-size: 11px;
                                       color: #6a6a6a; text-transform: uppercase; letter-spacing: 0.05em;
                                       border-bottom: 2px solid #e5e5e5;">Due</th>
                            <th style="padding: 10px 16px; text-align: left; font-size: 11px;
                                       color: #6a6a6a; text-transform: uppercase; letter-spacing: 0.05em;
                                       border-bottom: 2px solid #e5e5e5;">Priority</th>
                            <th style="padding: 10px 16px; text-align: left; font-size: 11px;
                                       color: #6a6a6a; text-transform: uppercase; letter-spacing: 0.05em;
                                       border-bottom: 2px solid #e5e5e5;">Source</th>
                        </tr>
                    </thead>
                    <tbody>
                        {task_rows}
                    </tbody>
                </table>

                <p style="font-size: 13px; color: #999; margin: 24px 0 0 0;">
                    Sent from EOS Platform on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}
                </p>
            </div>

            <!-- Footer -->
            <div style="background: #f8f9fa; padding: 16px 32px; border-top: 1px solid #e5e5e5;">
                <p style="font-size: 12px; color: #999; margin: 0;">
                    Steensma Inc. - EOS Platform
                </p>
            </div>
        </div>
    </body>
    </html>
    """


def build_task_text(tasks, recipient_name, division_name):
    """Build plain-text email for task notification"""
    lines = [
        f"EOS Platform - Task Assignment",
        f"Division: {division_name}",
        f"",
        f"Hello {recipient_name},",
        f"",
        f"You have {len(tasks)} assigned task{'s' if len(tasks) != 1 else ''}:",
        f"",
    ]
    for i, t in enumerate(tasks, 1):
        due = t.get('due_date', 'No due date') or 'No due date'
        lines.append(f"  {i}. {t.get('task', t.get('todo', ''))} [Due: {due}] [{t.get('priority', 'MEDIUM')}]")

    lines.append(f"")
    lines.append(f"Sent from EOS Platform on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    return "\n".join(lines)


def send_task_notification(to_email, recipient_name, tasks, division_name):
    """Send task assignment notification email.
    Returns (success, error_message)"""
    if not tasks:
        return False, "No tasks to notify about"

    subject = f"EOS: {len(tasks)} Task{'s' if len(tasks) != 1 else ''} Assigned - {division_name}"
    html = build_task_email_html(tasks, recipient_name, division_name)
    text = build_task_text(tasks, recipient_name, division_name)
    return send_email(to_email, subject, html, text)
