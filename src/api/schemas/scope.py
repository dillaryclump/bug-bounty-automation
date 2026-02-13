"""
Scope Schemas
Pydantic models for scope-related API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ScopeHistoryResponse(BaseModel):
    """Schema for scope history response."""
    
    id: int
    program_id: int
    in_scope: list[str]
    out_of_scope: list[str]
    changes: Optional[list[dict]] = None
    checksum: str
    source: Optional[str] = None
    checked_at: datetime
    
    # Change counts
    additions: int = 0
    removals: int = 0
    modifications: int = 0
    
    model_config = {"from_attributes": True}


class ScopeHistoryListResponse(BaseModel):
    """Schema for scope history list response."""
    
    total: int
    history: list[ScopeHistoryResponse]


class ScopeCheckRequest(BaseModel):
    """Schema for requesting a scope check."""
    
    program_id: int
    api_token: Optional[str] = None


class ScopeValidationResponse(BaseModel):
    """Schema for scope validation response."""
    
    asset: str
    in_scope: bool
    reason: str
    matched_rule: Optional[str] = None


class ScopeValidationListResponse(BaseModel):
    """Schema for batch validation response."""
    
    total: int
    in_scope_count: int
    out_scope_count: int
    results: list[ScopeValidationResponse]
