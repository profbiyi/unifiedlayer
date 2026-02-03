"""
Notification services for email and Slack.

Provides utilities for sending alerts and notifications
via email and Slack webhooks.
"""
import smtplib
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
        header_color_start: Optional[str] = None,
        header_color_end: Optional[str] = None,
        brand_primary_color: Optional[str] = None,
        brand_secondary_color: Optional[str] = None,
        logo_url: Optional[str] = None,
        organization_name: Optional[str] = None,
    ) -> str:
        """
        Generate a branded email HTML wrapper.

        Args:
            content: The main email content (HTML)
            header_title: Title for the header section
            header_color_start: Header gradient start color (defaults to brand_primary_color or #667eea)
            header_color_end: Header gradient end color (defaults to brand_secondary_color or #764ba2)
            brand_primary_color: Organization's primary brand color
            brand_secondary_color: Organization's secondary brand color
            logo_url: URL to organization's logo
            organization_name: Name of the organization

        Returns:
            Complete branded HTML email
        """
        # Use brand colors or defaults
        primary = brand_primary_color or "#667eea"
        secondary = brand_secondary_color or "#764ba2"

        # Header gradient: use specific colors if provided, otherwise use brand colors
        gradient_start = header_color_start or primary
        gradient_end = header_color_end or secondary

        # Logo section
        logo_html = ""
        if logo_url:
            logo_html = f'<img src="{logo_url}" alt="{organization_name or "Logo"}" style="max-height: 50px; margin-bottom: 15px;" />'

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #1f2937;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, {gradient_start} 0%, {gradient_end} 100%);
            color: white;
            padding: 30px;
            border-radius: 10px 10px 0 0;
            text-align: center;
        }}
        .content {{
            background: #f9fafb;
            padding: 30px;
            border-radius: 0 0 10px 10px;
        }}
        .button {{
            display: inline-block;
            padding: 14px 32px;
            background: {primary};
            color: white !important;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            margin: 20px 0;
        }}
        .details {{
            background: white;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
            border-left: 4px solid {primary};
        }}
        .stats {{
            background: white;
            padding: 20px;
            border-radius: 6px;
            margin: 20px 0;
            border-left: 4px solid {primary};
        }}
        .stat-item {{
            display: flex;
            justify-content: space-between;
            padding: 10px 0;
            border-bottom: 1px solid #e5e7eb;
        }}
        .stat-item:last-child {{
            border-bottom: none;
        }}
        .footer {{
            text-align: center;
            color: #6b7280;
            font-size: 14px;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }}
    </style>
</head>
<body>
    <div class="header">
        {logo_html}
        <h1 style="margin: 0;">{header_title}</h1>
    </div>

    <div class="content">
        {content}
    </div>

    <div class="footer">
        <p>{organization_name or "UnifiedLayer"} - Modern Data Integration</p>
        <p style="font-size: 12px;">© 2026 {organization_name or "UnifiedLayer"}. All rights reserved.</p>
    </div>
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
        if not self.smtp_host:
            logger.warning("SMTP not configured, skipping email notification")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_email
            msg["To"] = ", ".join(to_emails)
            msg["Subject"] = subject
            msg["Date"] = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

            # Attach body
            mime_type = "html" if html else "plain"
            msg.attach(MIMEText(body, mime_type))

            # Connect to SMTP server
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.use_tls:
                    server.starttls()

                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                server.send_message(msg)

            logger.info(f"Email sent to {to_emails}: {subject}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}")
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
        plain_body = f"""
You've been invited to join {organization_name}!

{invited_by_name} has invited you to join {organization_name} on UnifiedLayer.

Organization: {organization_name}
Role: {role_name}
Invited by: {invited_by_name}

Accept your invitation here:
{invitation_link}

Note: This invitation will expire in 7 days.

---
{organization_name} - Modern Data Integration
"""

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
        plain_body = f"""
Pipeline Completed Successfully ✅

Pipeline: {pipeline_name}
Status: SUCCESS

Run Details:
- Run ID: #{run_id}
- Records Processed: {records_processed:,}
- Duration: {duration_seconds:.1f}s

View details: {pipeline_url}

Great job! Your data pipeline is running smoothly.

---
{organization_name or "UnifiedLayer"} - Modern Data Integration
"""

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
        traceback_preview = error_traceback[:1000] + "..." if len(error_traceback) > 1000 else error_traceback

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
        plain_body = f"""
Pipeline Failed ❌

Pipeline: {pipeline_name}
Status: FAILED
Run ID: #{run_id}

Error:
{error_preview}

View full details: {pipeline_url}

Tip: Check the error logs for more details and verify your source/destination configurations.

---
{organization_name or "UnifiedLayer"} - Modern Data Integration
"""

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
        plain_body = f"""
Reset Your Password

Hi {user_name or "there"},

We received a request to reset your password for your {org_name} account.

Reset your password here:
{reset_link}

⏰ This link will expire in 1 hour.

If you didn't request a password reset, you can safely ignore this email.

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
