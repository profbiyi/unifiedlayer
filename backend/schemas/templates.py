"""
Pydantic schemas for template endpoints.
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class TemplateCredentialField(BaseModel):
    """Schema for a single credential field in a template."""
    field: str
    label: str
    type: str
    placeholder: str = ""
    required: bool = True
    options: Optional[List[str]] = None


class TemplateInfo(BaseModel):
    """Template summary returned in list views."""
    id: str
    name: str
    description: str
    category: str
    source_type: str
    destination_type: str
    icon: str
    tags: List[str]


class TemplateDetail(TemplateInfo):
    """Full template detail including credential schemas."""
    source_config_template: Dict[str, Any]
    destination_config_template: Dict[str, Any]
    source_credential_schema: List[TemplateCredentialField]
    destination_credential_schema: List[TemplateCredentialField]


class TemplateDeployRequest(BaseModel):
    """Request to deploy a template as a pipeline."""
    source_credentials: Dict[str, Any]
    destination_credentials: Dict[str, Any]
    pipeline_name: str
    schedule: Optional[str] = None


class TemplateDeployResponse(BaseModel):
    """Response after deploying a template."""
    pipeline_id: str
    source_id: str
    destination_id: str
    message: str
