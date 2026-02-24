"""
SQL Transformations API Routes.

Provides endpoints for managing SQL transformations that run after
data is loaded to the destination.
"""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, UUID4, field_validator
import uuid
import logging

from backend.database import get_db
from backend.models.transformation import SQLTransformation, TransformationStatus
from backend.models.pipeline import Pipeline, User
from backend.api.deps import get_current_user, check_permission, verify_org_access

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/pipelines",
    tags=["Transformations"],
)


# ==================== Pydantic Schemas ====================

class TransformationCreate(BaseModel):
    """Schema for creating a SQL transformation."""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the transformation")
    description: Optional[str] = Field(None, description="Description of what this transformation does")
    sql_query: str = Field(..., min_length=1, description="SQL query to execute")
    target_table: Optional[str] = Field(None, max_length=255, description="Target table for results")
    write_mode: Optional[str] = Field("replace", description="Write mode: replace, append, merge")
    execution_order: Optional[int] = Field(0, ge=0, description="Execution order (lower numbers execute first)")
    is_active: bool = Field(True, description="Whether this transformation is active")
    continue_on_error: bool = Field(False, description="Continue pipeline if this transform fails")
    timeout_seconds: int = Field(300, ge=0, le=3600, description="Timeout in seconds (0 = no timeout)")

    @field_validator('write_mode')
    @classmethod
    def validate_write_mode(cls, v):
        """Validate write mode."""
        allowed_modes = ['replace', 'append', 'merge']
        if v and v not in allowed_modes:
            raise ValueError(f"write_mode must be one of: {', '.join(allowed_modes)}")
        return v


class TransformationUpdate(BaseModel):
    """Schema for updating a SQL transformation."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    sql_query: Optional[str] = Field(None, min_length=1)
    target_table: Optional[str] = Field(None, max_length=255)
    write_mode: Optional[str] = None
    execution_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    continue_on_error: Optional[bool] = None
    timeout_seconds: Optional[int] = Field(None, ge=0, le=3600)

    @field_validator('write_mode')
    @classmethod
    def validate_write_mode(cls, v):
        """Validate write mode."""
        if v is None:
            return v
        allowed_modes = ['replace', 'append', 'merge']
        if v not in allowed_modes:
            raise ValueError(f"write_mode must be one of: {', '.join(allowed_modes)}")
        return v


class TransformationResponse(BaseModel):
    """Schema for transformation response."""
    id: int
    public_id: UUID4
    pipeline_id: int
    name: str
    description: Optional[str]
    sql_query: str
    target_table: Optional[str]
    write_mode: Optional[str]
    execution_order: int
    is_active: bool
    continue_on_error: bool
    timeout_seconds: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TransformationReorderItem(BaseModel):
    """Schema for a single reorder item."""
    transformation_id: str = Field(..., description="Transformation public ID (UUID)")
    execution_order: int = Field(..., ge=0, description="New execution order")


class TransformationReorderRequest(BaseModel):
    """Schema for reordering transformations."""
    transformations: List[TransformationReorderItem] = Field(..., min_length=1)


class SQLTestRequest(BaseModel):
    """Schema for testing SQL syntax."""
    sql_query: Optional[str] = Field(None, description="SQL query to test (if not using stored query)")


class SQLTestResponse(BaseModel):
    """Schema for SQL test response."""
    valid: bool
    message: str
    errors: Optional[List[str]] = None
    warnings: Optional[List[str]] = None
    parsed_tables: Optional[List[str]] = None


# ==================== Helper Functions ====================

def get_pipeline_by_public_id(
    pipeline_id: str,
    current_user: User,
    db: Session
) -> Pipeline:
    """Get pipeline by public ID with org access verification."""
    try:
        pipeline_uuid = uuid.UUID(pipeline_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid pipeline ID format"
        )

    pipeline = db.query(Pipeline).filter(
        Pipeline.public_id == pipeline_uuid
    ).first()

    if not pipeline:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pipeline not found"
        )

    verify_org_access(current_user, pipeline.organization_id, db)

    return pipeline


def get_transformation_by_public_id(
    transformation_id: str,
    pipeline: Pipeline,
    db: Session
) -> SQLTransformation:
    """Get transformation by public ID within a pipeline."""
    try:
        transformation_uuid = uuid.UUID(transformation_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid transformation ID format"
        )

    transformation = db.query(SQLTransformation).filter(
        SQLTransformation.public_id == transformation_uuid,
        SQLTransformation.pipeline_id == pipeline.id
    ).first()

    if not transformation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transformation not found"
        )

    return transformation


def validate_sql_syntax(sql_query: str) -> SQLTestResponse:
    """
    Validate SQL syntax using DuckDB's parser.

    DuckDB provides robust SQL parsing that can detect syntax errors
    without executing the query.
    """
    import duckdb

    errors = []
    warnings = []
    parsed_tables = []

    # Basic security checks
    sql_lower = sql_query.lower().strip()

    # Check for potentially dangerous operations
    dangerous_patterns = [
        ('drop database', 'DROP DATABASE statements are not allowed'),
        ('drop schema', 'DROP SCHEMA statements are not allowed'),
        ('truncate', 'TRUNCATE statements should be used with caution'),
        ('delete from', 'DELETE statements should be used with caution'),
    ]

    for pattern, warning in dangerous_patterns:
        if pattern in sql_lower:
            warnings.append(warning)

    # Validate using DuckDB's parser
    try:
        # Create an in-memory DuckDB connection for parsing only
        conn = duckdb.connect(':memory:')

        try:
            # Use EXPLAIN to validate syntax without executing
            # This will parse the SQL and report syntax errors
            explain_query = f"EXPLAIN {sql_query}"
            conn.execute(explain_query)
        except duckdb.ParserException as e:
            # Parser exception means syntax error
            error_msg = str(e)
            # Clean up the error message
            if 'Parser Error:' in error_msg:
                error_msg = error_msg.split('Parser Error:')[1].strip()
            errors.append(f"SQL syntax error: {error_msg}")
        except duckdb.CatalogException:
            # Catalog exception means tables/columns don't exist,
            # but syntax is valid - this is expected since we don't have schema
            pass
        except duckdb.BinderException:
            # Binder exception means references don't exist,
            # but syntax is valid - this is expected
            pass
        except Exception as e:
            # Other DuckDB errors might indicate issues
            error_type = type(e).__name__
            if 'Syntax' in error_type or 'Parser' in error_type:
                errors.append(f"SQL syntax error: {str(e)}")
            # Otherwise, syntax is likely valid
        finally:
            conn.close()

        # Try to extract table references using regex
        import re

        # Simple pattern to find table references (after FROM, JOIN, INTO)
        table_patterns = [
            r'\bFROM\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',
            r'\bJOIN\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',
            r'\bINTO\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',
            r'\bUPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*(?:\.[a-zA-Z_][a-zA-Z0-9_]*)?)',
        ]

        for pattern in table_patterns:
            matches = re.findall(pattern, sql_query, re.IGNORECASE)
            parsed_tables.extend(matches)

        # Deduplicate tables
        parsed_tables = list(set(parsed_tables))

    except ImportError:
        # DuckDB not available, fall back to basic validation
        warnings.append("DuckDB not available for full syntax validation")

        # Basic checks
        if not sql_query.strip():
            errors.append("SQL query cannot be empty")

        # Check for basic SQL structure
        sql_upper = sql_query.upper().strip()
        valid_starts = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP', 'WITH', 'MERGE']
        if not any(sql_upper.startswith(start) for start in valid_starts):
            warnings.append("Query does not start with a recognized SQL keyword")
    except Exception as e:
        logger.error(f"Error validating SQL: {str(e)}", exc_info=True)
        errors.append(f"Validation error: {str(e)}")

    is_valid = len(errors) == 0

    if is_valid:
        message = "SQL syntax is valid"
        if warnings:
            message += f" (with {len(warnings)} warning(s))"
    else:
        message = f"SQL syntax validation failed with {len(errors)} error(s)"

    return SQLTestResponse(
        valid=is_valid,
        message=message,
        errors=errors if errors else None,
        warnings=warnings if warnings else None,
        parsed_tables=parsed_tables if parsed_tables else None
    )


# ==================== API Endpoints ====================

@router.get("/{pipeline_id}/transformations", response_model=List[TransformationResponse])
def list_transformations(
    pipeline_id: str,
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all SQL transformations for a pipeline.

    Requires: pipelines.read permission

    Transformations are returned ordered by execution_order.
    """
    check_permission(current_user, "pipelines.read", db)
    pipeline = get_pipeline_by_public_id(pipeline_id, current_user, db)

    query = db.query(SQLTransformation).filter(
        SQLTransformation.pipeline_id == pipeline.id
    )

    if is_active is not None:
        query = query.filter(SQLTransformation.is_active == is_active)

    transformations = query.order_by(SQLTransformation.execution_order).all()

    return transformations


@router.post("/{pipeline_id}/transformations", response_model=TransformationResponse, status_code=status.HTTP_201_CREATED)
def create_transformation(
    pipeline_id: str,
    transformation: TransformationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new SQL transformation for a pipeline.

    Requires: pipelines.update permission

    The SQL query will be validated for syntax errors before creation.
    """
    check_permission(current_user, "pipelines.update", db)
    pipeline = get_pipeline_by_public_id(pipeline_id, current_user, db)

    # Validate SQL syntax
    validation_result = validate_sql_syntax(transformation.sql_query)
    if not validation_result.valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "message": "Invalid SQL syntax",
                "errors": validation_result.errors
            }
        )

    # Determine execution order if not specified
    if transformation.execution_order == 0:
        # Get the max execution order for this pipeline
        max_order = db.query(SQLTransformation).filter(
            SQLTransformation.pipeline_id == pipeline.id
        ).with_entities(SQLTransformation.execution_order).order_by(
            SQLTransformation.execution_order.desc()
        ).first()

        if max_order:
            transformation.execution_order = max_order[0] + 1

    # Create the transformation
    db_transformation = SQLTransformation(
        public_id=uuid.uuid4(),
        pipeline_id=pipeline.id,
        name=transformation.name,
        description=transformation.description,
        sql_query=transformation.sql_query,
        target_table=transformation.target_table,
        write_mode=transformation.write_mode,
        execution_order=transformation.execution_order,
        is_active=transformation.is_active,
        continue_on_error=transformation.continue_on_error,
        timeout_seconds=transformation.timeout_seconds,
    )

    db.add(db_transformation)
    db.commit()
    db.refresh(db_transformation)

    # Record column-level lineage from the SQL query
    try:
        _record_transformation_lineage(db, db_transformation, pipeline.organization_id)
    except Exception as e:
        logger.warning(f"Failed to record column lineage for transformation {db_transformation.id}: {e}")
        # Don't fail the creation if lineage recording fails

    logger.info(
        f"Created transformation '{db_transformation.name}' (id={db_transformation.id}) "
        f"for pipeline '{pipeline.name}' (id={pipeline.id})"
    )

    return db_transformation


@router.get("/{pipeline_id}/transformations/{transformation_id}", response_model=TransformationResponse)
def get_transformation(
    pipeline_id: str,
    transformation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific SQL transformation by ID.

    Requires: pipelines.read permission
    """
    check_permission(current_user, "pipelines.read", db)
    pipeline = get_pipeline_by_public_id(pipeline_id, current_user, db)
    transformation = get_transformation_by_public_id(transformation_id, pipeline, db)

    return transformation


@router.put("/{pipeline_id}/transformations/{transformation_id}", response_model=TransformationResponse)
def update_transformation(
    pipeline_id: str,
    transformation_id: str,
    update: TransformationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a SQL transformation.

    Requires: pipelines.update permission

    If sql_query is updated, it will be validated for syntax errors.
    """
    check_permission(current_user, "pipelines.update", db)
    pipeline = get_pipeline_by_public_id(pipeline_id, current_user, db)
    transformation = get_transformation_by_public_id(transformation_id, pipeline, db)

    # Validate SQL if being updated
    if update.sql_query is not None:
        validation_result = validate_sql_syntax(update.sql_query)
        if not validation_result.valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "message": "Invalid SQL syntax",
                    "errors": validation_result.errors
                }
            )

    # Update fields
    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(transformation, field, value)

    db.commit()
    db.refresh(transformation)

    # Re-record column-level lineage if SQL was updated
    if update.sql_query is not None:
        try:
            _record_transformation_lineage(db, transformation, pipeline.organization_id, refresh=True)
        except Exception as e:
            logger.warning(f"Failed to update column lineage for transformation {transformation.id}: {e}")

    logger.info(
        f"Updated transformation '{transformation.name}' (id={transformation.id}) "
        f"for pipeline '{pipeline.name}' (id={pipeline.id})"
    )

    return transformation


@router.delete("/{pipeline_id}/transformations/{transformation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transformation(
    pipeline_id: str,
    transformation_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a SQL transformation.

    Requires: pipelines.update permission
    """
    check_permission(current_user, "pipelines.update", db)
    pipeline = get_pipeline_by_public_id(pipeline_id, current_user, db)
    transformation = get_transformation_by_public_id(transformation_id, pipeline, db)

    logger.info(
        f"Deleting transformation '{transformation.name}' (id={transformation.id}) "
        f"from pipeline '{pipeline.name}' (id={pipeline.id})"
    )

    db.delete(transformation)
    db.commit()

    return None


@router.post("/{pipeline_id}/transformations/{transformation_id}/test", response_model=SQLTestResponse)
def test_transformation_sql(
    pipeline_id: str,
    transformation_id: str,
    test_request: Optional[SQLTestRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Test/validate SQL syntax for a transformation.

    Requires: pipelines.read permission

    If sql_query is provided in the request body, it validates that query.
    Otherwise, it validates the stored SQL query for the transformation.

    This uses DuckDB's parser to validate SQL syntax without executing the query.
    """
    check_permission(current_user, "pipelines.read", db)
    pipeline = get_pipeline_by_public_id(pipeline_id, current_user, db)
    transformation = get_transformation_by_public_id(transformation_id, pipeline, db)

    # Use provided SQL or the stored SQL
    sql_to_test = transformation.sql_query
    if test_request and test_request.sql_query:
        sql_to_test = test_request.sql_query

    if not sql_to_test or not sql_to_test.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No SQL query to test"
        )

    return validate_sql_syntax(sql_to_test)


@router.put("/{pipeline_id}/transformations/reorder", response_model=List[TransformationResponse])
def reorder_transformations(
    pipeline_id: str,
    reorder_request: TransformationReorderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reorder transformations for a pipeline.

    Requires: pipelines.update permission

    Provide a list of transformation IDs with their new execution orders.
    All transformations in the request must belong to the specified pipeline.
    """
    check_permission(current_user, "pipelines.update", db)
    pipeline = get_pipeline_by_public_id(pipeline_id, current_user, db)

    # Validate and update each transformation
    updated_transformations = []

    for item in reorder_request.transformations:
        transformation = get_transformation_by_public_id(item.transformation_id, pipeline, db)
        transformation.execution_order = item.execution_order
        updated_transformations.append(transformation)

    db.commit()

    # Refresh and return updated transformations
    for t in updated_transformations:
        db.refresh(t)

    logger.info(
        f"Reordered {len(updated_transformations)} transformations "
        f"for pipeline '{pipeline.name}' (id={pipeline.id})"
    )

    # Return all transformations for the pipeline in new order
    return db.query(SQLTransformation).filter(
        SQLTransformation.pipeline_id == pipeline.id
    ).order_by(SQLTransformation.execution_order).all()


def _record_transformation_lineage(
    db: Session,
    transformation: SQLTransformation,
    organization_id: int,
    refresh: bool = False,
) -> None:
    """
    Record column-level lineage from a SQL transformation.

    Args:
        db: Database session
        transformation: SQLTransformation to analyze
        organization_id: Organization ID for scoping
        refresh: If True, delete existing lineage before recording
    """
    from backend.services.column_lineage_service import ColumnLineageService

    service = ColumnLineageService(db)

    if refresh:
        # Delete existing lineage for this transformation
        service.delete_lineage_for_transformation(transformation.id)

    # Record new lineage
    lineages = service.record_transformation_lineage(
        transformation=transformation,
        organization_id=organization_id,
        dialect="postgres",  # Default dialect
    )

    logger.info(
        f"Recorded {len(lineages)} column lineage entries for transformation {transformation.id}"
    )
