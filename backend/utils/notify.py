"""
Notification helper utilities.

Provides a convenience function for creating notifications
from anywhere in the application (pipeline flows, billing, etc.).
"""
from typing import Optional
from sqlalchemy.orm import Session

from backend.models.notification import Notification


def create_notification(
    db: Session,
    user_id: int,
    org_id: int,
    type: str,
    title: str,
    message: str,
    link: Optional[str] = None,
) -> Notification:
    """
    Create and persist a new notification.

    Args:
        db: SQLAlchemy database session.
        user_id: The recipient user's internal ID.
        org_id: The organization ID.
        type: Notification type (pipeline_success, pipeline_failure,
              usage_warning, stale_data, billing_alert, team_invite).
        title: Short notification title (max 255 chars).
        message: Full notification message body.
        link: Optional in-app link (e.g. "/pipelines/<uuid>").

    Returns:
        The newly created Notification instance.
    """
    notification = Notification(
        user_id=user_id,
        organization_id=org_id,
        type=type,
        title=title,
        message=message,
        link=link,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification
