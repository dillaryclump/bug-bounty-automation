"""
Vulnerability Schemas
Pydantic models for vulnerability-related API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class VulnerabilityResponse(BaseModel):
    """Schema for vulnerability response."""
    
    id: int
    program_id: int
    asset_id: int
    template_id: str
    name: str
    severity: str
    matched_at: str
    curl_command: Optional[str] = None
    description: Optional[str] = None
    reference: Optional[str] = None
    cve_id: Optional[str] = None
    cvss_score: Optional[float] = None
    is_reported: bool
    reported_at: Optional[datetime] = None
    discovered_at: datetime
    
    # Asset details
    asset_value: Optional[str] = None
    asset_type: Optional[str] = None
    
    # Program details
    program_name: Optional[str] = None
    platform: Optional[str] = None
    
    model_config = {"from_attributes": True}


class VulnerabilityListResponse(BaseModel):
    """Schema for vulnerability list response."""
    
    total: int
    vulnerabilities: list[VulnerabilityResponse]
    
    # Severity breakdown
    severity_counts: dict[str, int] = Field(default_factory=dict)
    
    # Filters applied
    filters: dict = Field(default_factory=dict)


class VulnerabilityMarkReported(BaseModel):
    """Schema for marking vulnerabilities as reported."""
    
    vulnerability_ids: list[int]
    notes: Optional[str] = None
