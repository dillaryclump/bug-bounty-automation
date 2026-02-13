"""
Program Schemas
Pydantic models for program-related API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProgramBase(BaseModel):
    """Base program schema."""
    
    platform: str = Field(..., description="Platform (hackerone/bugcrowd)")
    handle: str = Field(..., description="Program handle/slug")
    name: str = Field(..., description="Program name")
    url: Optional[str] = Field(None, description="Program URL")
    is_active: bool = Field(default=True, description="Whether program is active")


class ProgramCreate(ProgramBase):
    """Schema for creating a program."""
    pass


class ProgramUpdate(BaseModel):
    """Schema for updating a program."""
    
    name: Optional[str] = None
    url: Optional[str] = None 
    is_active: Optional[bool] = None


class ProgramResponse(ProgramBase):
    """Schema for program response."""
    
    id: int
    created_at: datetime
    last_scanned: Optional[datetime] = None
    
    # Stats (computed)
    asset_count: Optional[int] = None
    vuln_count: Optional[int] = None
    critical_vuln_count: Optional[int] = None
    
    model_config = {"from_attributes": True}


class ProgramListResponse(BaseModel):
    """Schema for program list response."""
    
    total: int
    programs: list[ProgramResponse]
