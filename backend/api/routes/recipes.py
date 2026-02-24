"""
Pipeline Recipes API routes.

Provides endpoints for browsing and applying pipeline recipes.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.auth import get_current_user
from backend.database import get_db
from backend.models.pipeline import User
from backend.services.recipe_service import get_recipe_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/recipes", tags=["Pipeline Recipes"])


# ============================================================
# Schemas
# ============================================================

class TransformationInfo(BaseModel):
    name: str
    description: Optional[str] = None
    target_table: Optional[str] = None


class RecipeSummary(BaseModel):
    id: str
    name: str
    description: str
    category: str
    source_type: str
    icon: Optional[str] = None
    schedule_description: Optional[str] = None
    estimated_rows_per_day: Optional[int] = None
    available: Optional[bool] = None
    missing: Optional[str] = None


class RecipeDetail(BaseModel):
    id: str
    name: str
    description: str
    category: str
    source_type: str
    destination_type: Optional[str] = None
    icon: Optional[str] = None
    schedule: Optional[str] = None
    schedule_description: Optional[str] = None
    tables: List[str]
    transformations: List[TransformationInfo]
    estimated_rows_per_day: Optional[int] = None
    use_cases: Optional[List[str]] = None


class SourceInfo(BaseModel):
    required: str
    connected: bool
    source_id: Optional[int] = None
    source_name: Optional[str] = None


class DestinationInfo(BaseModel):
    id: int
    name: str
    type: str


class DestinationRequirement(BaseModel):
    required: str
    available: List[DestinationInfo]
    has_matching: bool


class RecipeRequirements(BaseModel):
    recipe_id: str
    recipe_name: str
    can_apply: bool
    source: SourceInfo
    destination: DestinationRequirement
    tables: List[str]
    transformations: int
    schedule: Optional[str] = None
    schedule_description: Optional[str] = None


class ApplyRecipeRequest(BaseModel):
    source_id: int
    destination_id: int
    name: Optional[str] = None
    schedule: Optional[str] = None


class ApplyRecipeResponse(BaseModel):
    success: bool
    pipeline: Optional[dict] = None
    transformations: Optional[List[str]] = None
    recipe_id: Optional[str] = None
    recipe_name: Optional[str] = None
    error: Optional[str] = None


class CategoryInfo(BaseModel):
    name: str
    description: str
    icon: str


# ============================================================
# Endpoints
# ============================================================

@router.get("/categories")
async def list_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, CategoryInfo]:
    """
    Get all recipe categories.
    """
    service = get_recipe_service(db)
    return service.get_all_categories()


@router.get("", response_model=List[RecipeSummary])
async def list_recipes(
    category: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all recipes with availability status.

    Recipes are marked as available if the required source type
    is connected and at least one destination is configured.

    Args:
        category: Optional filter by category (finance, accounting, banking, operations)
    """
    service = get_recipe_service(db)
    recipes = service.get_available_recipes(current_user.organization_id)

    if category:
        recipes = [r for r in recipes if r["category"] == category.lower()]

    return recipes


@router.get("/{recipe_id}")
async def get_recipe(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get full recipe details including transformations.
    """
    service = get_recipe_service(db)
    recipe = service.get_recipe_details(recipe_id)

    if not recipe:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recipe not found",
        )

    # Add requirements check
    requirements = service.check_recipe_requirements(
        current_user.organization_id,
        recipe_id,
    )
    recipe["requirements"] = requirements

    return recipe


@router.get("/{recipe_id}/requirements", response_model=RecipeRequirements)
async def check_recipe_requirements(
    recipe_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Check what's needed to apply a recipe.

    Returns information about required sources, available destinations,
    and whether the recipe can be applied.
    """
    service = get_recipe_service(db)
    requirements = service.check_recipe_requirements(
        current_user.organization_id,
        recipe_id,
    )

    if "error" in requirements:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=requirements["error"],
        )

    return requirements


@router.post("/{recipe_id}/apply", response_model=ApplyRecipeResponse)
async def apply_recipe(
    recipe_id: str,
    request: ApplyRecipeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Apply a recipe to create a pipeline.

    Creates a new pipeline with the recipe's configuration and
    adds any pre-defined SQL transformations.

    Args:
        recipe_id: Recipe ID to apply
        request: Source, destination, and optional customizations
    """
    service = get_recipe_service(db)

    # Check requirements first
    requirements = service.check_recipe_requirements(
        current_user.organization_id,
        recipe_id,
    )

    if "error" in requirements:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=requirements["error"],
        )

    if not requirements["can_apply"]:
        missing = []
        if not requirements["source"]["connected"]:
            missing.append(f"Connect a {requirements['source']['required']} source")
        if not requirements["destination"]["has_matching"]:
            missing.append("Set up a destination")

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot apply recipe: {', '.join(missing)}",
        )

    # Apply the recipe
    result = service.apply_recipe(
        org_id=current_user.organization_id,
        recipe_id=recipe_id,
        source_id=request.source_id,
        destination_id=request.destination_id,
        name=request.name,
        schedule=request.schedule,
        created_by_id=current_user.id,
    )

    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"],
        )

    return result
