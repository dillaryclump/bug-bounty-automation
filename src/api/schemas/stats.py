"""
Statistics Schemas
Pydantic models for dashboard statistics.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class DashboardStats(BaseModel):
    """Schema for dashboard statistics."""
    
    # Programs
    total_programs: int
    active_programs: int
    
    # Assets
    total_assets: int
    alive_assets: int
    in_scope_assets: int
    new_assets_24h: int
    
    # Vulnerabilities
    total_vulnerabilities: int
    new_vulnerabilities_24h: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    unreported_count: int
    
    # Scans
    total_scans: int
    scans_24h: int
    running_scans: int
    
    # Alerts
    alerts_sent_24h: int
    failed_alerts: int
    
    # Scope
    scope_changes_24h: int
    
    # Recent activity
    last_scan: Optional[datetime] = None
    last_vulnerability: Optional[datetime] = None
    last_scope_check: Optional[datetime] = None


class ProgramStats(BaseModel):
    """Schema for program-specific statistics."""
    
    program_id: int
    program_name: str
    platform: str
    
    # Assets
    total_assets: int
    alive_assets: int
    in_scope_assets: int
    
    # Vulnerabilities by severity  
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    info_count: int
    
    # Scans
    total_scans: int
    last_scan: Optional[datetime] = None
    
    # Scope
    in_scope_items: int
    out_scope_items: int
    last_scope_check: Optional[datetime] = None


class TimeSeriesDataPoint(BaseModel):
    """Schema for time series data point."""
    
    timestamp: datetime
    value: int


class TimeSeriesResponse(BaseModel):
    """Schema for time series data."""
    
    metric: str
    period: str  # "24h", "7d", "30d"
    data: list[TimeSeriesDataPoint]
