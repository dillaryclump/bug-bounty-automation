"""
Alert Schemas
Pydantic models for alert-related API endpoints.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class AlertResponse(BaseModel):
    """Schema for alert response."""
    
    id: int
    alert_type: str
    severity: Optional[str] = None
    title: str
    message: str
    channel: str
    destination: str
    sent: bool
    success: Optional[bool] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
    retry_count: int
    error_message: Optional[str] = None
    
    # Related entities
    program_id: Optional[int] = None
    vulnerability_id: Optional[int] = None
    asset_id: Optional[int] = None
    
    model_config = {"from_attributes": True}


class AlertListResponse(BaseModel):
    """Schema for alert list response."""
    
    total: int
    alerts: list[AlertResponse]


class AlertCreate(BaseModel):
    """Schema for creating an alert."""
    
    alert_type: str
    title: str
    message: str
    severity: Optional[str] = None
    program_id: Optional[int] = None


class AlertStatsResponse(BaseModel):
    """Schema for alert statistics."""
    
    total_sent: int
    total_failed: int
    by_type: dict[str, int]
    by_channel: dict[str, int]
    success_rate: float
