"""
User API routes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from backend.async_database import get_async_db
from backend.schemas import UserUpdate, UserResponse
from backend.models.pipeline import User
from backend.models.rbac import UserRole
from backend.auth import get_current_user, get_current_superuser
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])

# UserResponse serializes `roles` (from user_roles → role), so those relationships
# must be eager-loaded — AsyncSession cannot lazy-load during serialization.
_with_roles = selectinload(User.user_roles).selectinload(UserRole.role)


@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """List all users in the current user's organization."""
    result = await db.execute(
        select(User)
        .options(_with_roles)
        .where(User.organization_id == current_user.organization_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Get a specific user by ID."""
    user = (
        await db.execute(
            select(User)
            .options(_with_roles)
            .where(
                User.id == user_id,
                User.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Update a user (self or same organization)."""
    user = (
        await db.execute(
            select(User)
            .options(_with_roles)
            .where(
                User.id == user_id,
                User.organization_id == current_user.organization_id,
            )
        )
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Only allow self-update or superuser update
    if user.id != current_user.id and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough privileges",
        )

    update_data = user_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)

    await db.commit()
    # AsyncSessionLocal uses expire_on_commit=False, so `user` (incl. the eager
    # user_roles) stays loaded after commit — safe to serialize without a refresh.
    logger.info(f"User updated: {user.id} - {user.email}")
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_superuser),
    db: AsyncSession = Depends(get_async_db),
):
    """Delete a user (superuser only)."""
    user = (
        await db.execute(select(User).where(User.id == user_id))
    ).scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    await db.delete(user)
    await db.commit()

    logger.info(f"User deleted: {user_id}")
    return None
