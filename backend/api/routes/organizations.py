"""
Organization API routes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas import OrganizationCreate, OrganizationUpdate, OrganizationResponse
from backend.schemas.rbac import OrganizationBrandingUpdate
from backend.models.pipeline import Organization, User
from backend.auth import get_current_user, get_current_superuser
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/organizations", tags=["Organizations"])


@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """List all organizations (superuser only)."""
    organizations = db.query(Organization).offset(skip).limit(limit).all()
    return organizations


@router.get("/me", response_model=OrganizationResponse)
async def get_my_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get current user's organization."""
    organization = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return organization


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Get a specific organization by ID (superuser only)."""
    organization = db.query(Organization).filter(
        Organization.id == organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    return organization


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    org_data: OrganizationCreate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Create a new organization (superuser only)."""
    # Check if slug already exists
    existing = db.query(Organization).filter(
        Organization.slug == org_data.slug
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization slug already exists",
        )

    organization = Organization(
        name=org_data.name,
        slug=org_data.slug,
        description=org_data.description,
        is_active=True,
    )

    db.add(organization)
    db.commit()
    db.refresh(organization)

    logger.info(f"Organization created: {organization.id} - {organization.name}")
    return organization


@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: int,
    org_data: OrganizationUpdate,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Update an existing organization (superuser only)."""
    organization = db.query(Organization).filter(
        Organization.id == organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    update_data = org_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(organization, field, value)

    db.commit()
    db.refresh(organization)

    logger.info(f"Organization updated: {organization.id} - {organization.name}")
    return organization


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: int,
    current_user: User = Depends(get_current_superuser),
    db: Session = Depends(get_db),
):
    """Delete an organization (superuser only)."""
    organization = db.query(Organization).filter(
        Organization.id == organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Protect the platform organization from deletion
    if organization.slug == "platform":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete the platform organization",
        )

    db.delete(organization)
    db.commit()

    logger.info(f"Organization deleted: {organization_id}")
    return None


@router.patch("/me/branding", response_model=OrganizationResponse)
async def update_my_organization_branding(
    branding: OrganizationBrandingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update current organization's branding.

    Requires ORG_ADMIN role.

    Allows updating:
    - Logo URL
    - Primary brand color (hex code)
    - Secondary brand color (hex code)
    """

    # Check if user is org admin
    if not current_user.is_org_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization admins can update branding"
        )

    organization = db.query(Organization).filter(
        Organization.id == current_user.organization_id
    ).first()

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found",
        )

    # Update branding fields
    if branding.logo_url is not None:
        organization.logo_url = branding.logo_url
    if branding.brand_primary_color is not None:
        organization.brand_primary_color = branding.brand_primary_color
    if branding.brand_secondary_color is not None:
        organization.brand_secondary_color = branding.brand_secondary_color

    db.commit()
    db.refresh(organization)

    logger.info(f"Organization branding updated: {organization.id}")
    return organization
