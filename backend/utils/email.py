"""
Email utility for sending transactional emails.

Uses SMTP settings from config. Gracefully fails if SMTP is not configured.
"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from backend.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_body: str) -> bool:
    """
    Send an email using SMTP settings from config.

    Args:
        to: Recipient email address
        subject: Email subject
        html_body: HTML email body

    Returns:
        True if sent successfully, False otherwise
    """
    if not settings.SMTP_HOST or not settings.SMTP_FROM_EMAIL:
        logger.warning(
            "SMTP not configured (SMTP_HOST or SMTP_FROM_EMAIL missing). "
            "Skipping email to %s with subject: %s",
            to,
            subject,
        )
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM_EMAIL
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to, msg.as_string())
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.warning("Failed to send email to %s: %s", to, str(e))
        return False


def send_verification_email(to: str, token: str) -> bool:
    """
    Send an email verification email with a link to verify the user's email address.

    Args:
        to: Recipient email address
        token: Verification token

    Returns:
        True if sent successfully, False otherwise
    """
    frontend_url = settings.FRONTEND_URL
    verification_url = f"{frontend_url}/verify-email?token={token}"

    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
        <h2 style="color: #1a1a1a;">Verify your email address</h2>
        <p style="color: #4a4a4a; font-size: 16px;">
            Thanks for signing up for {settings.APP_NAME}! Please verify your email
            address by clicking the button below.
        </p>
        <div style="text-align: center; margin: 32px 0;">
            <a href="{verification_url}"
               style="background-color: #3B82F6; color: white; padding: 12px 32px;
                      text-decoration: none; border-radius: 6px; font-size: 16px;">
                Verify Email
            </a>
        </div>
        <p style="color: #6a6a6a; font-size: 14px;">
            Or copy and paste this link into your browser:<br/>
            <a href="{verification_url}" style="color: #3B82F6;">{verification_url}</a>
        </p>
        <p style="color: #999; font-size: 12px; margin-top: 32px;">
            If you did not create an account, you can safely ignore this email.
        </p>
    </div>
    """

    return send_email(to, f"Verify your email - {settings.APP_NAME}", html_body)
