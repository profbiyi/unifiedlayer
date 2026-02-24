"""
Pagination Utilities.

Standardized pagination response format for API endpoints.
"""
from typing import TypeVar, Generic, List, Any, Dict
from pydantic import BaseModel

T = TypeVar('T')


class PaginationInfo(BaseModel):
    """Pagination metadata."""
    total: int
    skip: int
    limit: int
    has_more: bool


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standardized paginated response format.

    Attributes:
        data: List of items for the current page
        pagination: Pagination metadata (total, skip, limit, has_more)
    """
    data: List[Any]
    pagination: PaginationInfo


def paginate(items: List, total: int, skip: int, limit: int) -> Dict[str, Any]:
    """
    Create a standardized paginated response.

    Args:
        items: List of items for the current page
        total: Total number of items across all pages
        skip: Number of items skipped (offset)
        limit: Maximum number of items per page

    Returns:
        Dictionary with 'data' and 'pagination' keys in standardized format

    Example:
        >>> items = [{"id": 1}, {"id": 2}]
        >>> response = paginate(items, total=10, skip=0, limit=2)
        >>> response
        {
            "data": [{"id": 1}, {"id": 2}],
            "pagination": {
                "total": 10,
                "skip": 0,
                "limit": 2,
                "has_more": True
            }
        }
    """
    return {
        "data": items,
        "pagination": {
            "total": total,
            "skip": skip,
            "limit": limit,
            "has_more": skip + len(items) < total
        }
    }


def paginate_query(query, skip: int, limit: int) -> Dict[str, Any]:
    """
    Paginate a SQLAlchemy query and return standardized response.

    Args:
        query: SQLAlchemy query object
        skip: Number of items to skip
        limit: Maximum number of items to return

    Returns:
        Dictionary with 'data' and 'pagination' keys
    """
    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return paginate(items, total, skip, limit)
