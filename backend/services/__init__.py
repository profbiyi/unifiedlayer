"""
UnifiedLayer Services Module.

Contains business logic services for the platform.
"""
from backend.services.dashboard_service import DashboardService, get_dashboard_service
from backend.services.recipe_service import RecipeService, get_recipe_service
from backend.services.auto_dashboard_service import AutoDashboardService, get_auto_dashboard_service

__all__ = [
    "DashboardService",
    "get_dashboard_service",
    "RecipeService",
    "get_recipe_service",
    "AutoDashboardService",
    "get_auto_dashboard_service",
]
