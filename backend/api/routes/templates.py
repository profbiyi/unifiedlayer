"""
Templates API routes.

Provides endpoints for browsing and deploying pre-built pipeline templates.
"""
from typing import List
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.auth import get_current_user
from backend.models.pipeline import (
    DataSource, Destination, Pipeline, User, SourceType, DestinationType,
)
from backend.schemas.templates import (
    TemplateInfo, TemplateDetail, TemplateDeployRequest, TemplateDeployResponse,
)
from backend.templates.data import get_all_templates, get_template_by_id

import logging
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/templates", tags=["Templates"])


@router.get("/", response_model=List[TemplateInfo])
def list_templates():
    """List all available sync templates. No auth required."""
    return get_all_templates()


@router.get("/{template_id}", response_model=TemplateDetail)
def get_template(template_id: str):
    """Get a single template by ID."""
    template = get_template_by_id(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )
    return template


@router.post("/{template_id}/deploy", response_model=TemplateDeployResponse)
def deploy_template(
    template_id: str,
    request: TemplateDeployRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Deploy a template: creates DataSource + Destination + Pipeline in one transaction.
    Requires authentication.
    """
    template = get_template_by_id(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found",
        )

    try:
        # Merge user credentials with template defaults
        source_config = {**template["source_config_template"], **request.source_credentials}
        dest_config = {**template["destination_config_template"], **request.destination_credentials}

        # Resolve enum values — use the string value and let SQLAlchemy handle it
        source_type_str = template["source_type"]
        dest_type_str = template["destination_type"]

        # Create DataSource
        source = DataSource(
            public_id=uuid.uuid4(),
            organization_id=current_user.organization_id,
            name=f"{template['name']} Source",
            description=f"Auto-created from template: {template['name']}",
            source_type=source_type_str,
            config=source_config,
        )
        db.add(source)
        db.flush()

        # Create Destination
        destination = Destination(
            public_id=uuid.uuid4(),
            organization_id=current_user.organization_id,
            name=f"{template['name']} Destination",
            description=f"Auto-created from template: {template['name']}",
            destination_type=dest_type_str,
            config=dest_config,
        )
        db.add(destination)
        db.flush()

        # Create Pipeline
        pipeline = Pipeline(
            public_id=uuid.uuid4(),
            organization_id=current_user.organization_id,
            source_id=source.id,
            destination_id=destination.id,
            name=request.pipeline_name or f"{template['name']} Pipeline",
            description=f"Pipeline created from template: {template['name']}",
            schedule=request.schedule,
        )
        db.add(pipeline)
        db.commit()
        db.refresh(pipeline)
        db.refresh(source)
        db.refresh(destination)

        logger.info(
            f"Template '{template_id}' deployed: pipeline={pipeline.public_id}, "
            f"source={source.public_id}, destination={destination.public_id}"
        )

        return TemplateDeployResponse(
            pipeline_id=str(pipeline.public_id),
            source_id=str(source.public_id),
            destination_id=str(destination.public_id),
            message=f"Successfully deployed '{template['name']}' template",
        )

    except Exception as e:
        db.rollback()
        logger.error(f"Failed to deploy template '{template_id}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy template: {str(e)}",
        )
