"""
Recipe Service.

Manages pipeline recipes - pre-configured pipeline templates for common use cases.
"""
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.pipeline import DataSource, Destination, Pipeline
from backend.models.transformation import SQLTransformation
from backend.templates.pipeline_recipes import (
    RECIPE_CATEGORIES,
    get_all_recipes,
    get_recipe_by_id,
    get_recipes_by_category,
)

logger = logging.getLogger(__name__)


class RecipeService:
    """Service for managing and applying pipeline recipes."""

    def __init__(self, db: Session):
        self.db = db

    def get_all_recipes(self) -> List[Dict[str, Any]]:
        """Get all available recipes."""
        return get_all_recipes()

    def get_all_categories(self) -> Dict[str, Dict[str, str]]:
        """Get all recipe categories."""
        return RECIPE_CATEGORIES

    def get_recipes_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get recipes in a specific category."""
        return get_recipes_by_category(category)

    def get_recipe_details(self, recipe_id: str) -> Optional[Dict[str, Any]]:
        """Get full recipe details."""
        recipe = get_recipe_by_id(recipe_id)
        if recipe:
            return {"id": recipe_id, **recipe}
        return None

    def get_available_recipes(self, org_id: int) -> List[Dict[str, Any]]:
        """
        Get recipes with availability status based on connected sources.

        Args:
            org_id: Organization ID

        Returns:
            List of recipes with 'available' and 'source' fields
        """
        # Get connected sources
        sources = self.db.query(DataSource).filter(
            DataSource.organization_id == org_id,
            DataSource.is_active,
        ).all()

        source_types = {s.source_type.lower(): s for s in sources}

        # Get destinations
        destinations = self.db.query(Destination).filter(
            Destination.organization_id == org_id,
            Destination.is_active,
        ).all()

        has_destination = len(destinations) > 0

        # Mark recipes as available/unavailable
        recipes = []
        for recipe in get_all_recipes():
            recipe_copy = recipe.copy()
            required_source = recipe["source_type"].lower()

            if required_source in source_types:
                recipe_copy["available"] = True
                recipe_copy["connected_source"] = {
                    "id": source_types[required_source].id,
                    "name": source_types[required_source].name,
                }
            else:
                recipe_copy["available"] = False
                recipe_copy["connected_source"] = None
                recipe_copy["missing"] = f"Connect a {recipe['source_type']} source"

            recipe_copy["has_destination"] = has_destination
            if not has_destination:
                recipe_copy["available"] = False
                recipe_copy["missing"] = recipe_copy.get("missing", "") + " and set up a destination"

            recipes.append(recipe_copy)

        return recipes

    def check_recipe_requirements(
        self,
        org_id: int,
        recipe_id: str,
    ) -> Dict[str, Any]:
        """
        Check what's needed to apply a recipe.

        Args:
            org_id: Organization ID
            recipe_id: Recipe ID

        Returns:
            Dict with requirements status
        """
        recipe = get_recipe_by_id(recipe_id)
        if not recipe:
            return {"error": "Recipe not found"}

        # Check source
        required_source = recipe["source_type"].lower()
        source = self.db.query(DataSource).filter(
            DataSource.organization_id == org_id,
            DataSource.source_type.ilike(required_source),
            DataSource.is_active,
        ).first()

        # Check destinations
        destinations = self.db.query(Destination).filter(
            Destination.organization_id == org_id,
            Destination.is_active,
        ).all()

        # Check for specific destination type if required
        required_dest = recipe.get("destination_type")
        matching_destinations = destinations
        if required_dest:
            matching_destinations = [
                d for d in destinations
                if d.destination_type.lower() == required_dest.lower()
            ]

        return {
            "recipe_id": recipe_id,
            "recipe_name": recipe["name"],
            "can_apply": source is not None and len(matching_destinations) > 0,
            "source": {
                "required": recipe["source_type"],
                "connected": source is not None,
                "source_id": source.id if source else None,
                "source_name": source.name if source else None,
            },
            "destination": {
                "required": required_dest or "any",
                "available": [
                    {"id": d.id, "name": d.name, "type": d.destination_type}
                    for d in matching_destinations
                ],
                "has_matching": len(matching_destinations) > 0,
            },
            "tables": recipe.get("tables", []),
            "transformations": len(recipe.get("transformations", [])),
            "schedule": recipe.get("schedule"),
            "schedule_description": recipe.get("schedule_description"),
        }

    def apply_recipe(
        self,
        org_id: int,
        recipe_id: str,
        source_id: int,
        destination_id: int,
        name: Optional[str] = None,
        schedule: Optional[str] = None,
        created_by_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Apply a recipe to create a pipeline with transformations.

        Args:
            org_id: Organization ID
            recipe_id: Recipe ID
            source_id: Source to use
            destination_id: Destination to use
            name: Optional custom pipeline name
            schedule: Optional custom schedule (overrides recipe default)
            created_by_id: User ID creating the pipeline

        Returns:
            Created pipeline info
        """
        recipe = get_recipe_by_id(recipe_id)
        if not recipe:
            return {"error": "Recipe not found"}

        # Verify source and destination belong to org
        source = self.db.query(DataSource).filter(
            DataSource.id == source_id,
            DataSource.organization_id == org_id,
        ).first()

        if not source:
            return {"error": "Source not found or not accessible"}

        destination = self.db.query(Destination).filter(
            Destination.id == destination_id,
            Destination.organization_id == org_id,
        ).first()

        if not destination:
            return {"error": "Destination not found or not accessible"}

        try:
            # Create pipeline
            pipeline_name = name or f"{recipe['name']} - {source.name}"
            pipeline_schedule = schedule or recipe.get("schedule")

            pipeline = Pipeline(
                name=pipeline_name,
                description=recipe["description"],
                organization_id=org_id,
                source_id=source_id,
                destination_id=destination_id,
                schedule=pipeline_schedule,
                sync_mode="incremental",
                tables=recipe.get("tables", []),
                is_active=True,
                created_by_id=created_by_id,
                created_at=datetime.now(timezone.utc),
            )

            self.db.add(pipeline)
            self.db.flush()  # Get pipeline ID

            # Create transformations
            transformations_created = []
            for transform in recipe.get("transformations", []):
                sql_transform = SQLTransformation(
                    pipeline_id=pipeline.id,
                    name=transform["name"],
                    description=transform.get("description"),
                    sql_query=transform["sql"],
                    target_table=transform.get("target_table"),
                    execution_order=transform.get("execution_order", 1),
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                )
                self.db.add(sql_transform)
                transformations_created.append(transform["name"])

            self.db.commit()

            logger.info(
                f"Applied recipe '{recipe_id}' for org {org_id}: "
                f"pipeline {pipeline.id} with {len(transformations_created)} transformations"
            )

            return {
                "success": True,
                "pipeline": {
                    "id": pipeline.id,
                    "name": pipeline.name,
                    "description": pipeline.description,
                    "schedule": pipeline.schedule,
                },
                "transformations": transformations_created,
                "recipe_id": recipe_id,
                "recipe_name": recipe["name"],
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to apply recipe {recipe_id}: {e}")
            return {"error": str(e)}


def get_recipe_service(db: Session) -> RecipeService:
    """Factory function for RecipeService."""
    return RecipeService(db)
