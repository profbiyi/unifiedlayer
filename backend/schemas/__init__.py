"""
Pydantic schemas for API request/response validation.
"""
# Import all schemas from base module
from backend.schemas.base import *

# Import Column Lineage schemas
from backend.schemas.column_lineage import (
    ColumnLineageBase,
    ColumnLineageCreate,
    ColumnLineageResponse,
    ColumnDependencyResponse,
    ColumnLineageGraphNode,
    ColumnLineageGraphEdge,
    ColumnLineageGraphResponse,
    ColumnImpactSummary,
    AffectedPipeline,
    ColumnImpactAnalysisResponse,
    DbtColumnMetadataResponse,
    ParseSQLRequest,
    ParseSQLResponse,
    TableColumnLineageRequest,
    RefreshLineageResponse,
)

# Import RBAC schemas
from backend.schemas.rbac import (
    # Role schemas
    RoleResponse,

    # User schemas
    UserWithRoles,
    UserListItem,
    ChangeUserRoleRequest,

    # Invitation schemas
    CreateInvitationRequest,
    AcceptInvitationRequest,
    InvitationResponse,
    InvitationPublicResponse,

    # Organization schemas
    OrganizationWithStats,
    OrganizationSubscriptionUpdate,
    CreateOrganizationRequest,
    OrganizationCreatedResponse,

    # Admin schemas
    PlatformStats,
)

__all__ = [
    # Base schemas (from base.py)
    "UTCDatetimeMixin",
    "TokenData",
    "UserLogin",
    "UserBase",
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "Token",
    "OrganizationBase",
    "OrganizationCreate",
    "OrganizationUpdate",
    "OrganizationResponse",
    "DataSourceBase",
    "DataSourceCreate",
    "DataSourceUpdate",
    "DataSourceResponse",
    "DestinationBase",
    "DestinationCreate",
    "DestinationUpdate",
    "DestinationResponse",
    "PipelineBase",
    "PipelineCreate",
    "PipelineUpdate",
    "PipelineResponse",
    "PipelineRunCreate",
    "PipelineRunUpdate",
    "PipelineRunResponse",
    "LineageNodeBase",
    "LineageNodeCreate",
    "LineageNodeResponse",
    "LineageEdgeBase",
    "LineageEdgeCreate",
    "LineageEdgeResponse",
    "LineageGraphResponse",

    # RBAC schemas (from rbac.py)
    "RoleResponse",
    "UserWithRoles",
    "UserListItem",
    "ChangeUserRoleRequest",
    "CreateInvitationRequest",
    "AcceptInvitationRequest",
    "InvitationResponse",
    "InvitationPublicResponse",
    "OrganizationWithStats",
    "OrganizationSubscriptionUpdate",
    "CreateOrganizationRequest",
    "OrganizationCreatedResponse",
    "PlatformStats",

    # Column Lineage schemas
    "ColumnLineageBase",
    "ColumnLineageCreate",
    "ColumnLineageResponse",
    "ColumnDependencyResponse",
    "ColumnLineageGraphNode",
    "ColumnLineageGraphEdge",
    "ColumnLineageGraphResponse",
    "ColumnImpactSummary",
    "AffectedPipeline",
    "ColumnImpactAnalysisResponse",
    "DbtColumnMetadataResponse",
    "ParseSQLRequest",
    "ParseSQLResponse",
    "TableColumnLineageRequest",
    "RefreshLineageResponse",
]
