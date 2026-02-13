"""
Scan Schemas
Pydantic models for scan-related API endpoints.
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class ScanType(str, Enum):
    """Scan type enumeration."""
    
    RECON_FULL = "recon_full"
    RECON_QUICK = "recon_quick"
    VULN_SCAN = "vuln_scan"
    SCOPE_CHECK = "scope_check"


class ScanStatus(str, Enum):
    """Scan status enumeration."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanResponse(BaseModel):
    """Schema for scan response."""
    
    id: int
    program_id: int
    scan_type: ScanType
    status: ScanStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Results
    assets_found: Optional[int] = None
    vulnerabilities_found: Optional[int] = None
    errors: Optional[list[str]] = None
    
    # Program details
    program_name: Optional[str] = None
    
    model_config = {"from_attributes": True}


class ScanListResponse(BaseModel):
    """Schema for scan list response."""
    
    total: int
    scans: list[ScanResponse]


class ScanCreateRequest(BaseModel):
    """Schema for creating a scan."""
    
    program_id: int
    scan_type: ScanType
    force: bool = Field(default=False, description="Force full rescan")
