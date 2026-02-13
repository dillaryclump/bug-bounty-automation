"""
Asset Schemas
Pydantic models for asset-related API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AssetResponse(BaseModel):
    """Schema for asset response."""
    
    id: int
    program_id: int
    value: str
    asset_type: str
    is_alive: bool
    in_scope: bool
    discovered_at: datetime
    last_seen: Optional[datetime] = None
    
    # HTTP probing data
    status_code: Optional[int] = None
    content_length: Optional[int] = None
    page_title: Optional[str] = None
    technologies: Optional[list[str]] = None
    
    # DNS data
    ip_addresses: Optional[list[str]] = None
    
    # Port data
    open_ports: Optional[list[int]] = None
    
    # Vulnerability count
    vuln_count: Optional[int] = None
    critical_vuln_count: Optional[int] = None
    
    model_config = {"from_attributes": True}


class AssetListResponse(BaseModel):
    """Schema for asset list response."""
    
    total: int
    assets: list[AssetResponse]
    
    # Filters applied
    filters: dict = Field(default_factory=dict)
