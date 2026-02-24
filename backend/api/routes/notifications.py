"""
Notification API routes.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
import uuid as uuid_mod

from backend.database import get_db
from backend.models.pipeline import User
from backend.models.notification import Notification
from backend.auth import get_current_user

router = APIRouter(prefix="/notifications", tags=["Notifications"])


# --- Pydantic schemas ---

class NotificationResponse(BaseModel):
    id: int
    public_id: uuid_mod.UUID
    type: str
    title: str
    message: str
    link: Optional[str] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


class UnreadCountResponse(BaseModel):
    unread: int


class PaginatedNotifications(BaseModel):
    items: List[NotificationResponse]
    total: int
    skip: int
    limit: int


# --- Endpoints ---

@router.get("", response_model=PaginatedNotifications)
async def list_notifications(
    unread_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List notifications for the current user."""
    query = db.query(Notification).filter(
        Notification.user_id == current_user.id,
    )
    if unread_only:
        query = query.filter(not Notification.is_read)

    total = query.count()
    items = query.order_by(Notification.created_at.desc()).offset(skip).limit(limit).all()

    return PaginatedNotifications(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/count", response_model=UnreadCountResponse)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the number of unread notifications for the current user."""
    count = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        not Notification.is_read,
    ).count()
    return UnreadCountResponse(unread=count)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    ).first()

    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return NotificationResponse.model_validate(notification)


@router.post("/mark-all-read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    updated = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        not Notification.is_read,
    ).update({"is_read": True})
    db.commit()
    return {"marked": updated}
