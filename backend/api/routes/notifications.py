"""
Notification API routes.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from datetime import datetime
import uuid as uuid_mod

from backend.async_database import get_async_db
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
    db: AsyncSession = Depends(get_async_db),
):
    """List notifications for the current user."""
    conds = [Notification.user_id == current_user.id]
    if unread_only:
        conds.append(Notification.is_read.is_(False))

    total = await db.scalar(
        select(func.count()).select_from(Notification).where(*conds)
    )
    result = await db.execute(
        select(Notification)
        .where(*conds)
        .order_by(Notification.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()

    return PaginatedNotifications(
        items=[NotificationResponse.model_validate(n) for n in items],
        total=total or 0,
        skip=skip,
        limit=limit,
    )


@router.get("/count", response_model=UnreadCountResponse)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Return the number of unread notifications for the current user."""
    count = await db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
    )
    return UnreadCountResponse(unread=count or 0)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Mark a single notification as read."""
    result = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)
    return NotificationResponse.model_validate(notification)


@router.post("/mark-all-read")
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Mark all notifications as read for the current user."""
    result = await db.execute(
        update(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()
    return {"marked": result.rowcount}
