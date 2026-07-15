"""
Notification services for email and Slack.

Provides utilities for sending alerts and notifications
via email and Slack webhooks.
"""
import smtplib
import json
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional, Dict, Any
import requests
import logging
from datetime import datetime

from backend.config import settings

logger = logging.getLogger(__name__)


class EmailNotificationError(Exception):
    """Email notification error."""
    pass


class SlackNotificationError(Exception):
    """Slack notification error."""
    pass


class EmailNotifier:
    """
    Email notification service.

    Sends email notifications via SMTP.
    """

    def __init__(self):
        """Initialize email notifier with settings."""
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL
        self.use_tls = settings.SMTP_USE_TLS

    def get_branded_template(
        self,
        content: str,
        header_title: str,
        header_subtitle: Optional[str] = None,
        header_color_start: Optional[str] = None,
        header_color_end: Optional[str] = None,
        brand_primary_color: Optional[str] = None,
        brand_secondary_color: Optional[str] = None,
        logo_url: Optional[str] = None,
        organization_name: Optional[str] = None,
    ) -> str:
        """
        Generate a modern, clean branded email HTML wrapper.
        """
        primary = brand_primary_color or "#6366f1"
        secondary = brand_secondary_color or "#8b5cf6"
        gradient_start = header_color_start or primary
        gradient_end = header_color_end or secondary

        subtitle_html = f'<p style="margin: 10px 0 0 0; opacity: 0.9; font-size: 16px;">{header_subtitle}</p>' if header_subtitle else ''

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{header_title}</title>
</head>
<body style="margin: 0; padding: 0; background-color: #f3f4f6; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #f3f4f6;">
        <tr>
            <td align="center" style="padding: 40px 20px;">
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; background-color: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">

                    <!-- Header -->
                    <tr>
                        <td style="background: linear-gradient(135deg, {gradient_start} 0%, {gradient_end} 100%); padding: 48px 40px; text-align: center;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <img src="https://img.icons8.com/fluency/96/data-configuration.png" alt="UnifiedLayer" width="56" height="56" style="margin-bottom: 16px;">
                                        <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700; letter-spacing: -0.5px;">{header_title}</h1>
                                        {subtitle_html}
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                    <!-- Content -->
                    <tr>
                        <td style="padding: 40px;">
                            {content}
                        </td>
                    </tr>

                    <!-- Footer -->
                    <tr>
                        <td style="background-color: #f9fafb; padding: 32px 40px; border-top: 1px solid #e5e7eb;">
                            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                                <tr>
                                    <td align="center">
                                        <p style="margin: 0 0 8px 0; color: #6b7280; font-size: 14px;">
                                            Powered by <strong style="color: #374151;">UnifiedLayer</strong>
                                        </p>
                                        <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                            The data platform for modern businesses
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>

                </table>

                <!-- Bottom Links -->
                <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width: 600px; margin-top: 24px;">
                    <tr>
                        <td align="center">
                            <p style="margin: 0; color: #9ca3af; font-size: 12px;">
                                © 2026 UnifiedLayer. All rights reserved.
                            </p>
                        </td>
                    </tr>
                </table>
            </td>
        </tr>
    </table>
</body>
</html>
"""

    def send(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html: bool = False,
    ) -> bool:
        """
        Send an email notification.

        Uses SendGrid API if SENDGRID_API_KEY is configured (recommended for cloud),
        otherwise falls back to SMTP.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Email body
            html: Whether body is HTML

        Returns:
            True if email sent successfully

        Raises:
            EmailNotificationError: If email sending fails
        """
        # Provider chain: Resend (Railway's recommended HTTPS API) → SendGrid
        # → SMTP. Railway blocks outbound SMTP below the Pro plan, so an
        # HTTPS provider must come first; each failure falls through to the
        # next configured provider so one stale key can't kill notifications.
        last_error: Optional[EmailNotificationError] = None

        if settings.RESEND_API_KEY:
            try:
                return self._send_via_resend(to_emails, subject, body, html)
            except EmailNotificationError as e:
                last_error = e
                logger.warning("Resend send failed; trying next email provider")

        if settings.SENDGRID_API_KEY:
            try:
                return self._send_via_sendgrid(to_emails, subject, body, html)
            except EmailNotificationError as e:
                last_error = e
                logger.warning("SendGrid send failed; trying next email provider")

        if self.smtp_host:
            return self._send_via_smtp(to_emails, subject, body, html)

        if last_error:
            raise last_error

        logger.warning(
            "No email provider configured (RESEND_API_KEY, SENDGRID_API_KEY or SMTP_HOST)"
        )
        return False

    def _send_via_resend(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html: bool = False,
    ) -> bool:
        """Send email via the Resend HTTPS API (https://resend.com/docs/api-reference)."""
        try:
            payload: Dict[str, Any] = {
                "from": f"UnifiedLayer <{self.from_email}>",
                "to": to_emails,
                "subject": subject,
            }
            payload["html" if html else "text"] = body
            data = json.dumps(payload).encode()

            req = urllib.request.Request(
                "https://api.resend.com/emails",
                data=data,
                headers={
                    "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                    "Content-Type": "application/json",
                },
            )

            urllib.request.urlopen(req, timeout=30)
            logger.info(f"Email sent via Resend to {to_emails}: {subject}")
            return True

        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else str(e)
            logger.error(f"Resend API error: {e.code} - {error_body}")
            raise EmailNotificationError(f"Resend error: {error_body}")
        except Exception as e:
            logger.error(f"Failed to send email via Resend: {str(e)}")
            raise EmailNotificationError(f"Failed to send email: {str(e)}")

    def _send_via_sendgrid(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html: bool = False,
    ) -> bool:
        """Send email via SendGrid API."""
        try:
            content_type = "text/html" if html else "text/plain"
            data = json.dumps({
                "personalizations": [{"to": [{"email": email} for email in to_emails]}],
                "from": {"email": self.from_email, "name": "UnifiedLayer"},
                "subject": subject,
                "content": [{"type": content_type, "value": body}]
            }).encode()

            req = urllib.request.Request(
                "https://api.sendgrid.com/v3/mail/send",
                data=data,
                headers={
                    "Authorization": f"Bearer {settings.SENDGRID_API_KEY}",
                    "Content-Type": "application/json"
                }
            )

            urllib.request.urlopen(req, timeout=30)
            logger.info(f"Email sent via SendGrid to {to_emails}: {subject}")
            return True

        except urllib.error.HTTPError as e:
            error_body = e.read().decode() if e.fp else str(e)
            logger.error(f"SendGrid API error: {e.code} - {error_body}")
            raise EmailNotificationError(f"SendGrid error: {error_body}")
        except Exception as e:
            logger.error(f"Failed to send email via SendGrid: {str(e)}")
            raise EmailNotificationError(f"Failed to send email: {str(e)}")

    def _send_via_smtp(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        html: bool = False,
    ) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = subject
            msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

            mime_type = "html" if html else "plain"
            msg.attach(MIMEText(body, mime_type))

            # Use SMTP_SSL for port 465, regular SMTP with STARTTLS for port 587
            if self.smtp_port == 465:
                with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30) as server:
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as server:
                    if self.use_tls:
                        server.starttls()
                    if self.smtp_user and self.smtp_password:
                        server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)

            logger.info(f"Email sent via SMTP to {to_emails}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {str(e)}")
            raise EmailNotificationError(f"Failed to send email: {str(e)}")

    def send_pipeline_success(
        self,
        to_emails: List[str],
        pipeline_name: str,
        run_id: int,
        rows_processed: int,
    ) -> bool:
        """
        Send pipeline success notification.

        Args:
            to_emails: Recipient emails
            pipeline_name: Name of the pipeline
            run_id: Pipeline run ID
            rows_processed: Number of rows processed

        Returns:
            True if sent successfully
        """
        subject = f"✅ Pipeline Success: {pipeline_name}"
        body = f"""
Pipeline: {pipeline_name}
Run ID: {run_id}
Status: SUCCESS
Rows Processed: {rows_processed:,}
Timestamp: {datetime.utcnow().isoformat()}

The pipeline completed successfully.
"""
        return self.send(to_emails, subject, body)

    def send_pipeline_failure(
        self,
        to_emails: List[str],
        pipeline_name: str,
        run_id: int,
        error_message: str,
    ) -> bool:
        """
        Send pipeline failure notification.

        Args:
            to_emails: Recipient emails
            pipeline_name: Name of the pipeline
            run_id: Pipeline run ID
            error_message: Error message

        Returns:
            True if sent successfully
        """
        subject = f"❌ Pipeline Failure: {pipeline_name}"
        body = f"""
Pipeline: {pipeline_name}
Run ID: {run_id}
Status: FAILED
Error: {error_message}
Timestamp: {datetime.utcnow().isoformat()}

The pipeline failed. Please investigate.
"""
        return self.send(to_emails, subject, body)

    def send_invitation_email(
        self,
        to_email: str,
        organization_name: str,
        invited_by_name: str,
        invitation_link: str,
        role_name: str,
        logo_url: Optional[str] = None,
        brand_primary_color: Optional[str] = None,
        brand_secondary_color: Optional[str] = None,
    ) -> bool:
        """
        Send organization invitation email.

        Args:
            to_email: Recipient email address
            organization_name: Name of the organization
            invited_by_name: Name of person who sent the invite
            invitation_link: Full URL to accept invitation
            role_name: Role being assigned (Admin or User)
            logo_url: Organization logo URL (optional)
            brand_primary_color: Organization primary color (optional)
            brand_secondary_color: Organization secondary color (optional)

        Returns:
            True if sent successfully
        """
        subject = f"You've been invited to join {organization_name}"

        # Email content
        primary = brand_primary_color or "#667eea"
        content = f"""
        <p>Hi there,</p>

        <p><strong>{invited_by_name}</strong> has invited you to join <strong>{organization_name}</strong> on UnifiedLayer.</p>

        <div class="details">
            <p><strong>Organization:</strong> {organization_name}</p>
            <p><strong>Role:</strong> {role_name}</p>
            <p><strong>Invited by:</strong> {invited_by_name}</p>
        </div>

        <p>Click the button below to accept your invitation and create your account:</p>

        <center>
            <a href="{invitation_link}" class="button">Accept Invitation</a>
        </center>

        <p style="color: #6b7280; font-size: 14px;">
            <strong>Note:</strong> This invitation will expire in 7 days. If you did not expect this invitation, you can safely ignore this email.
        </p>

        <p style="color: #6b7280; font-size: 14px;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{invitation_link}" style="color: {primary}; word-break: break-all;">{invitation_link}</a>
        </p>
"""

        html_body = self.get_branded_template(
            content=content,
            header_title="🎉 You're Invited!",
            brand_primary_color=brand_primary_color,
            brand_secondary_color=brand_secondary_color,
            logo_url=logo_url,
            organization_name=organization_name,
        )

        # Plain text version as fallback

        return self.send([to_email], subject, html_body, html=True)

    def send_pipeline_success_email(
        self,
        to_email: str,
        pipeline_name: str,
        run_id: int,
        records_processed: int,
        duration_seconds: float,
        pipeline_url: str,
        organization_name: Optional[str] = None,
        logo_url: Optional[str] = None,
        brand_primary_color: Optional[str] = None,
        brand_secondary_color: Optional[str] = None,
    ) -> bool:
        """
        Send pipeline success notification email.

        Args:
            to_email: Recipient email address
            pipeline_name: Name of the pipeline
            run_id: Pipeline run ID
            records_processed: Number of records processed
            duration_seconds: Duration in seconds
            pipeline_url: URL to view pipeline details
            organization_name: Organization name (optional)
            logo_url: Organization logo URL (optional)
            brand_primary_color: Organization primary color (optional, used for button)
            brand_secondary_color: Organization secondary color (optional)

        Returns:
            True if sent successfully
        """
        subject = f"✅ Pipeline Success: {pipeline_name}"

        # Use green for success badge and stats border (always green for success)
        # But use brand color for button if provided
        button_color = brand_primary_color or "#10b981"

        # Email content with success-specific styling
        content = f"""
        <style>
            .success-badge {{
                display: inline-block;
                background: #d1fae5;
                color: #065f46;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 14px;
            }}
            .button {{
                background: {button_color} !important;
            }}
            .stats {{
                border-left-color: #10b981 !important;
            }}
        </style>

        <center>
            <span class="success-badge">SUCCESS</span>
        </center>

        <h2 style="color: #1f2937; margin-top: 20px;">{pipeline_name}</h2>

        <p>Your pipeline has completed successfully!</p>

        <div class="stats">
            <div class="stat-item">
                <span style="color: #6b7280;">Run ID</span>
                <strong>#{run_id}</strong>
            </div>
            <div class="stat-item">
                <span style="color: #6b7280;">Records Processed</span>
                <strong>{records_processed:,}</strong>
            </div>
            <div class="stat-item">
                <span style="color: #6b7280;">Duration</span>
                <strong>{duration_seconds:.1f}s</strong>
            </div>
        </div>

        <center>
            <a href="{pipeline_url}" class="button">View Pipeline Details</a>
        </center>

        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            Great job! Your data pipeline is running smoothly. 🎉
        </p>
"""

        html_body = self.get_branded_template(
            content=content,
            header_title="✅ Pipeline Completed Successfully",
            header_color_start="#10b981",  # Green gradient for success
            header_color_end="#059669",
            brand_primary_color=brand_primary_color,
            brand_secondary_color=brand_secondary_color,
            logo_url=logo_url,
            organization_name=organization_name,
        )

        # Plain text version

        return self.send([to_email], subject, html_body, html=True)

    def send_pipeline_failure_email(
        self,
        to_email: str,
        pipeline_name: str,
        run_id: int,
        error_message: str,
        error_traceback: str,
        pipeline_url: str,
        organization_name: Optional[str] = None,
        logo_url: Optional[str] = None,
        brand_primary_color: Optional[str] = None,
        brand_secondary_color: Optional[str] = None,
    ) -> bool:
        """
        Send pipeline failure notification email.

        Args:
            to_email: Recipient email address
            pipeline_name: Name of the pipeline
            run_id: Pipeline run ID
            error_message: Error message
            error_traceback: Error traceback
            pipeline_url: URL to view pipeline details
            organization_name: Organization name (optional)
            logo_url: Organization logo URL (optional)
            brand_primary_color: Organization primary color (optional, used for button)
            brand_secondary_color: Organization secondary color (optional)

        Returns:
            True if sent successfully
        """
        subject = f"❌ Pipeline Failed: {pipeline_name}"

        # Truncate error messages if too long
        error_preview = error_message[:500] + "..." if len(error_message) > 500 else error_message
        error_traceback[:1000] + "..." if len(error_traceback) > 1000 else error_traceback

        # Use red for error badge and box (always red for errors)
        # But use brand color for button if provided
        button_color = brand_primary_color or "#ef4444"

        # Email content with failure-specific styling
        content = f"""
        <style>
            .error-badge {{
                display: inline-block;
                background: #fee2e2;
                color: #991b1b;
                padding: 8px 16px;
                border-radius: 20px;
                font-weight: 600;
                font-size: 14px;
            }}
            .error-box {{
                background: #fef2f2;
                padding: 20px;
                border-radius: 6px;
                margin: 20px 0;
                border-left: 4px solid #ef4444;
            }}
            .error-message {{
                background: #fee2e2;
                padding: 15px;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 13px;
                color: #991b1b;
                overflow-x: auto;
                margin-top: 10px;
            }}
            .button {{
                background: {button_color} !important;
            }}
        </style>

        <center>
            <span class="error-badge">FAILED</span>
        </center>

        <h2 style="color: #1f2937; margin-top: 20px;">{pipeline_name}</h2>

        <p>Your pipeline encountered an error and failed to complete.</p>

        <div class="error-box">
            <p style="margin: 0 0 5px 0;"><strong>Run ID:</strong> #{run_id}</p>
            <p style="margin: 0 0 10px 0;"><strong>Error:</strong></p>
            <div class="error-message">{error_preview}</div>
        </div>

        <center>
            <a href="{pipeline_url}" class="button">View Full Error Details</a>
        </center>

        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            💡 <strong>Tip:</strong> Check the error logs for more details and verify your source/destination configurations.
        </p>
"""

        html_body = self.get_branded_template(
            content=content,
            header_title="❌ Pipeline Failed",
            header_color_start="#ef4444",  # Red gradient for failure
            header_color_end="#dc2626",
            brand_primary_color=brand_primary_color,
            brand_secondary_color=brand_secondary_color,
            logo_url=logo_url,
            organization_name=organization_name,
        )

        # Plain text version

        return self.send([to_email], subject, html_body, html=True)

    def send_welcome_email(
        self,
        to_email: str,
        user_name: str,
        organization_name: str,
        login_url: str,
        temporary_password: str,
        logo_url: Optional[str] = None,
        brand_primary_color: Optional[str] = None,
        brand_secondary_color: Optional[str] = None,
    ) -> bool:
        """
        Send welcome email to new organization admin with login credentials.
        """
        subject = "Welcome to UnifiedLayer - Your account is ready"

        primary = brand_primary_color or "#6366f1"

        content = f"""
            <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 24px 0;">
                Hi {user_name},
            </p>

            <p style="color: #374151; font-size: 16px; line-height: 1.6; margin: 0 0 32px 0;">
                Great news! Your organization <strong>{organization_name}</strong> is now live on UnifiedLayer.
                You've been set up as the administrator with full access to manage your data platform.
            </p>

            <!-- Credentials Card -->
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-radius: 12px; margin-bottom: 32px;">
                <tr>
                    <td style="padding: 24px;">
                        <p style="margin: 0 0 16px 0; color: #64748b; font-size: 12px; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                            Your Login Credentials
                        </p>
                        <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="padding: 8px 0;">
                                    <span style="color: #64748b; font-size: 14px;">Email</span><br>
                                    <strong style="color: #1e293b; font-size: 16px;">{to_email}</strong>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 8px 0; border-top: 1px solid #e2e8f0;">
                                    <span style="color: #64748b; font-size: 14px;">Temporary Password</span><br>
                                    <code style="background: #ffffff; color: #1e293b; font-size: 18px; font-weight: 600; padding: 8px 16px; border-radius: 6px; display: inline-block; margin-top: 4px; border: 1px solid #e2e8f0; letter-spacing: 1px;">{temporary_password}</code>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- CTA Button -->
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-bottom: 32px;">
                <tr>
                    <td align="center">
                        <a href="{login_url}" style="display: inline-block; background: linear-gradient(135deg, {primary} 0%, #8b5cf6 100%); color: #ffffff; text-decoration: none; padding: 16px 48px; border-radius: 8px; font-size: 16px; font-weight: 600; box-shadow: 0 4px 14px rgba(99, 102, 241, 0.4);">
                            Get Started →
                        </a>
                    </td>
                </tr>
            </table>

            <!-- Warning -->
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background-color: #fffbeb; border-radius: 8px; margin-bottom: 32px;">
                <tr>
                    <td style="padding: 16px 20px;">
                        <table role="presentation" cellspacing="0" cellpadding="0">
                            <tr>
                                <td style="vertical-align: top; padding-right: 12px;">
                                    <span style="font-size: 20px;">🔐</span>
                                </td>
                                <td>
                                    <p style="margin: 0; color: #92400e; font-size: 14px; font-weight: 500;">
                                        Please change your password after your first login for security.
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </td>
                </tr>
            </table>

            <!-- Features -->
            <p style="color: #374151; font-size: 14px; font-weight: 600; margin: 0 0 16px 0;">
                What you can do as an admin:
            </p>
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0">
                <tr>
                    <td style="padding: 8px 0; color: #4b5563; font-size: 14px;">
                        <span style="color: {primary}; margin-right: 8px;">✓</span> Connect data sources (Postgres, APIs, SaaS tools)
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #4b5563; font-size: 14px;">
                        <span style="color: {primary}; margin-right: 8px;">✓</span> Build automated data pipelines
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #4b5563; font-size: 14px;">
                        <span style="color: {primary}; margin-right: 8px;">✓</span> Invite team members to collaborate
                    </td>
                </tr>
                <tr>
                    <td style="padding: 8px 0; color: #4b5563; font-size: 14px;">
                        <span style="color: {primary}; margin-right: 8px;">✓</span> Monitor data quality and lineage
                    </td>
                </tr>
            </table>

            <p style="color: #9ca3af; font-size: 13px; margin: 32px 0 0 0;">
                Button not working? Copy this link: <a href="{login_url}" style="color: {primary};">{login_url}</a>
            </p>
"""

        html_body = self.get_branded_template(
            content=content,
            header_title="Welcome Aboard!",
            header_subtitle=f"Your {organization_name} account is ready",
            brand_primary_color=brand_primary_color,
            brand_secondary_color=brand_secondary_color,
            logo_url=logo_url,
            organization_name=organization_name,
        )


        return self.send([to_email], subject, html_body, html=True)

    def send_password_reset_email(
        self,
        to_email: str,
        reset_link: str,
        user_name: str,
        organization_name: Optional[str] = None,
        logo_url: Optional[str] = None,
        brand_primary_color: Optional[str] = None,
        brand_secondary_color: Optional[str] = None,
    ) -> bool:
        """
        Send password reset email.

        Args:
            to_email: Recipient email address
            reset_link: Password reset URL
            user_name: User's name
            organization_name: Organization name (optional)
            logo_url: Organization logo URL (optional)
            brand_primary_color: Organization primary color (optional)
            brand_secondary_color: Organization secondary color (optional)

        Returns:
            True if sent successfully
        """
        org_name = organization_name or "UnifiedLayer"
        subject = f"Reset Your Password - {org_name}"

        # Use brand color for button and links
        primary = brand_primary_color or "#667eea"

        # Email content
        content = f"""
        <style>
            .warning {{
                background: #fef3c7;
                border-left: 4px solid #f59e0b;
                padding: 15px;
                border-radius: 4px;
                margin: 20px 0;
            }}
        </style>

        <p>Hi {user_name or "there"},</p>

        <p>We received a request to reset your password for your {org_name} account. If you didn't make this request, you can safely ignore this email.</p>

        <center>
            <a href="{reset_link}" class="button">Reset Password</a>
        </center>

        <div class="warning">
            <p style="margin: 0;"><strong>⏰ This link will expire in 1 hour</strong></p>
            <p style="margin: 5px 0 0 0; font-size: 14px;">For security reasons, password reset links are only valid for 1 hour.</p>
        </div>

        <p style="color: #6b7280; font-size: 14px;">
            If the button doesn't work, copy and paste this link into your browser:<br>
            <a href="{reset_link}" style="color: {primary}; word-break: break-all;">{reset_link}</a>
        </p>

        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            If you didn't request a password reset, please ignore this email or contact support if you have concerns.
        </p>
"""

        html_body = self.get_branded_template(
            content=content,
            header_title="🔐 Reset Your Password",
            brand_primary_color=brand_primary_color,
            brand_secondary_color=brand_secondary_color,
            logo_url=logo_url,
            organization_name=organization_name,
        )

        # Plain text version

        return self.send([to_email], subject, html_body, html=True)

    def send_2fa_disabled_notification(
        self,
        to_email: str,
        user_name: str,
        organization_name: Optional[str] = None,
        logo_url: Optional[str] = None,
        brand_primary_color: Optional[str] = None,
        brand_secondary_color: Optional[str] = None,
    ) -> bool:
        """
        Send notification when 2FA is disabled.

        This is a security notification to alert users when their
        two-factor authentication has been turned off.

        Args:
            to_email: Recipient email address
            user_name: User's name
            organization_name: Organization name (optional)
            logo_url: Organization logo URL (optional)
            brand_primary_color: Organization primary color (optional)
            brand_secondary_color: Organization secondary color (optional)

        Returns:
            True if sent successfully
        """
        org_name = organization_name or "UnifiedLayer"
        subject = f"Security Alert: Two-Factor Authentication Disabled - {org_name}"

        # Email content
        content = f"""
        <style>
            .security-alert {{
                background: #fef2f2;
                border-left: 4px solid #ef4444;
                padding: 15px;
                border-radius: 4px;
                margin: 20px 0;
            }}
            .info-box {{
                background: #f3f4f6;
                padding: 15px;
                border-radius: 4px;
                margin: 20px 0;
            }}
        </style>

        <p>Hi {user_name or "there"},</p>

        <div class="security-alert">
            <p style="margin: 0;"><strong>🔓 Two-Factor Authentication Disabled</strong></p>
            <p style="margin: 10px 0 0 0; font-size: 14px;">
                Two-factor authentication (2FA) has been disabled on your {org_name} account.
                This was performed at <strong>{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</strong>.
            </p>
        </div>

        <p><strong>If you made this change:</strong></p>
        <p style="color: #6b7280; font-size: 14px;">
            No action is required. However, we strongly recommend keeping 2FA enabled for better account security.
        </p>

        <p><strong>If you did NOT make this change:</strong></p>
        <div class="info-box">
            <p style="margin: 0; font-size: 14px;">
                1. Immediately change your password<br>
                2. Re-enable two-factor authentication<br>
                3. Review your recent account activity<br>
                4. Contact support if you suspect unauthorized access
            </p>
        </div>

        <p style="color: #6b7280; font-size: 14px; margin-top: 30px;">
            This email was sent automatically as a security measure. If you have any questions, please contact our support team.
        </p>
"""

        html_body = self.get_branded_template(
            content=content,
            header_title="🔐 Security Alert",
            header_subtitle="Two-factor authentication has been disabled",
            header_color_start="#ef4444",  # Red gradient for security alert
            header_color_end="#dc2626",
            brand_primary_color=brand_primary_color,
            brand_secondary_color=brand_secondary_color,
            logo_url=logo_url,
            organization_name=organization_name,
        )

        # Plain text version
        f"""
Security Alert: Two-Factor Authentication Disabled

Hi {user_name or "there"},

Two-factor authentication (2FA) has been disabled on your {org_name} account.
This was performed at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC.

If you made this change:
No action is required. However, we strongly recommend keeping 2FA enabled.

If you did NOT make this change:
1. Immediately change your password
2. Re-enable two-factor authentication
3. Review your recent account activity
4. Contact support if you suspect unauthorized access

---
{org_name} - Modern Data Integration
"""

        return self.send([to_email], subject, html_body, html=True)


class SlackNotifier:
    """
    Slack notification service.

    Sends notifications via Slack webhooks.
    """

    def __init__(self):
        """Initialize Slack notifier with settings."""
        self.webhook_url = settings.SLACK_WEBHOOK_URL
        self.channel = settings.SLACK_CHANNEL

    def send(
        self,
        message: str,
        channel: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Send a Slack notification.

        Args:
            message: Message text
            channel: Slack channel (optional, uses default if not provided)
            attachments: Slack message attachments

        Returns:
            True if notification sent successfully

        Raises:
            SlackNotificationError: If notification sending fails
        """
        if not self.webhook_url:
            logger.warning("Slack webhook not configured, skipping notification")
            return False

        try:
            payload = {
                "text": message,
                "channel": channel or self.channel,
            }

            if attachments:
                payload["attachments"] = attachments

            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10,
            )
            response.raise_for_status()

            logger.info(f"Slack notification sent: {message[:100]}")
            return True

        except Exception as e:
            logger.error(f"Failed to send Slack notification: {str(e)}")
            raise SlackNotificationError(f"Failed to send Slack notification: {str(e)}")

    def send_pipeline_success(
        self,
        pipeline_name: str,
        run_id: int,
        rows_processed: int,
    ) -> bool:
        """
        Send pipeline success notification.

        Args:
            pipeline_name: Name of the pipeline
            run_id: Pipeline run ID
            rows_processed: Number of rows processed

        Returns:
            True if sent successfully
        """
        message = f":white_check_mark: Pipeline *{pipeline_name}* completed successfully"
        attachments = [
            {
                "color": "good",
                "fields": [
                    {"title": "Pipeline", "value": pipeline_name, "short": True},
                    {"title": "Run ID", "value": str(run_id), "short": True},
                    {"title": "Rows Processed", "value": f"{rows_processed:,}", "short": True},
                    {"title": "Status", "value": "SUCCESS", "short": True},
                ],
                "footer": "UnifiedLayer",
                "ts": int(datetime.utcnow().timestamp()),
            }
        ]

        return self.send(message, attachments=attachments)

    def send_pipeline_failure(
        self,
        pipeline_name: str,
        run_id: int,
        error_message: str,
    ) -> bool:
        """
        Send pipeline failure notification.

        Args:
            pipeline_name: Name of the pipeline
            run_id: Pipeline run ID
            error_message: Error message

        Returns:
            True if sent successfully
        """
        message = f":x: Pipeline *{pipeline_name}* failed"
        attachments = [
            {
                "color": "danger",
                "fields": [
                    {"title": "Pipeline", "value": pipeline_name, "short": True},
                    {"title": "Run ID", "value": str(run_id), "short": True},
                    {"title": "Status", "value": "FAILED", "short": True},
                    {"title": "Error", "value": error_message[:500], "short": False},
                ],
                "footer": "UnifiedLayer",
                "ts": int(datetime.utcnow().timestamp()),
            }
        ]

        return self.send(message, attachments=attachments)


# Global instances
email_notifier = EmailNotifier()
slack_notifier = SlackNotifier()


def send_notification(
    message: str,
    email_recipients: Optional[List[str]] = None,
    use_slack: bool = True,
) -> None:
    """
    Send notification via all configured channels.

    Args:
        message: Notification message
        email_recipients: Email recipients (optional)
        use_slack: Whether to send to Slack
    """
    if email_recipients:
        try:
            email_notifier.send(email_recipients, "UnifiedLayer Notification", message)
        except EmailNotificationError as e:
            logger.error(f"Email notification failed: {str(e)}")

    if use_slack:
        try:
            slack_notifier.send(message)
        except SlackNotificationError as e:
            logger.error(f"Slack notification failed: {str(e)}")


# ---------------------------------------------------------------------------
# WhatsApp Notification (Twilio)
# ---------------------------------------------------------------------------

# Guard the Twilio import — it's optional. If the package is not installed,
# WhatsApp notifications will be disabled and a warning will be logged once.
try:
    from twilio.rest import Client as TwilioClient
    _TWILIO_AVAILABLE = True
except ImportError:  # pragma: no cover
    _TWILIO_AVAILABLE = False


class WhatsAppNotificationError(Exception):
    """Raised when a WhatsApp notification cannot be delivered."""
    pass


class WhatsAppNotifier:
    """
    WhatsApp notification service powered by the Twilio API.

    Requires the following environment variables (all optional — the notifier
    degrades gracefully when they are absent):

        TWILIO_ACCOUNT_SID      — Twilio account SID
        TWILIO_AUTH_TOKEN       — Twilio auth token
        TWILIO_WHATSAPP_FROM    — Sender number in Twilio format,
                                   e.g. "whatsapp:+14155238886"
    """

    def __init__(self) -> None:
        """Initialise the notifier from application settings."""
        self.account_sid: Optional[str] = settings.TWILIO_ACCOUNT_SID
        self.auth_token: Optional[str] = settings.TWILIO_AUTH_TOKEN
        self.from_number: Optional[str] = settings.TWILIO_WHATSAPP_FROM
        self._client: Optional[Any] = None  # Lazy-initialised Twilio client

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_configured(self) -> bool:
        """Return True when all required Twilio credentials are present."""
        return bool(self.account_sid and self.auth_token and self.from_number)

    def _get_client(self):
        """Return a (cached) Twilio REST client, or None if unavailable."""
        if not _TWILIO_AVAILABLE:
            logger.warning(
                "twilio package is not installed. "
                "Install it with: pip install 'twilio>=9.0.0'"
            )
            return None

        if not self._is_configured():
            logger.warning(
                "Twilio credentials not configured. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, and "
                "TWILIO_WHATSAPP_FROM to enable WhatsApp notifications."
            )
            return None

        if self._client is None:
            self._client = TwilioClient(self.account_sid, self.auth_token)

        return self._client

    @staticmethod
    def _normalise_number(to_number: str) -> str:
        """
        Ensure the destination number carries the ``whatsapp:`` scheme prefix.

        Twilio requires recipients to be expressed as ``whatsapp:+<digits>``.
        This helper accepts either the raw E.164 number or the prefixed form.
        """
        if not to_number.startswith("whatsapp:"):
            # Strip any stray whitespace and ensure a leading "+"
            number = to_number.strip()
            if not number.startswith("+"):
                number = f"+{number}"
            return f"whatsapp:{number}"
        return to_number

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_whatsapp(self, to_number: str, message: str) -> bool:
        """
        Send a plain-text WhatsApp message via Twilio.

        Args:
            to_number: Recipient phone number in E.164 format (``+2348012345678``)
                       or already prefixed with ``whatsapp:+``.
            message:   Text body of the WhatsApp message.

        Returns:
            ``True`` when the message was accepted by Twilio, ``False``
            when credentials are missing / the package is not installed.

        Raises:
            WhatsAppNotificationError: When Twilio returns an error.
        """
        client = self._get_client()
        if client is None:
            return False

        recipient = self._normalise_number(to_number)

        try:
            msg = client.messages.create(
                body=message,
                from_=self.from_number,
                to=recipient,
            )
            logger.info(
                "WhatsApp message sent to %s (SID: %s)",
                recipient,
                msg.sid,
            )
            return True
        except Exception as exc:
            logger.error(
                "Failed to send WhatsApp message to %s: %s",
                recipient,
                str(exc),
            )
            raise WhatsAppNotificationError(
                f"Failed to send WhatsApp message: {exc}"
            ) from exc


# Global instance — mirrors the pattern used by EmailNotifier / SlackNotifier
whatsapp_notifier = WhatsAppNotifier()


def send_whatsapp_notification(
    to_number: str,
    title: str,
    message: str,
) -> bool:
    """
    Module-level helper to send a WhatsApp notification.

    Formats the title and message into a single body string and dispatches
    it via the global ``WhatsAppNotifier`` instance. Errors are logged as
    warnings so callers do not need to handle them.

    Args:
        to_number: Recipient phone number (E.164 or ``whatsapp:+`` prefixed).
        title:     Short heading for the notification (e.g. "Pipeline Failed").
        message:   Longer description / detail.

    Returns:
        ``True`` if the message was delivered, ``False`` otherwise.
    """
    body = f"*{title}*\n\n{message}\n\n— UnifiedLayer"
    try:
        return whatsapp_notifier.send_whatsapp(to_number, body)
    except WhatsAppNotificationError as exc:
        logger.warning("WhatsApp notification skipped: %s", str(exc))
        return False
