"""
Pydantic Schemas
Request/response models for API endpoints.
"""

from src.api.schemas.programs import ProgramCreate, ProgramUpdate, ProgramResponse
from src.api.schemas.assets import AssetResponse, AssetListResponse
from src.api.schemas.vulnerabilities import VulnerabilityResponse, VulnerabilityListResponse
from src.api.schemas.scans import ScanResponse, ScanStatus
from src.api.schemas.alerts import AlertResponse, AlertCreate
from src.api.schemas.scope import ScopeHistoryResponse, ScopeCheckRequest
from src.api.schemas.stats import DashboardStats, ProgramStats

__all__ = [
    # Programs
    "ProgramCreate",
    "ProgramUpdate",
    "ProgramResponse",
    # Assets
    "AssetResponse",
    "AssetListResponse",
    # Vulnerabilities
    "VulnerabilityResponse",
    "VulnerabilityListResponse",
    # Scans
    "ScanResponse",
    "ScanStatus",
    # Alerts
    "AlertResponse",
    "AlertCreate",
    # Scope
    "ScopeHistoryResponse",
    "ScopeCheckRequest",
    # Stats
    "DashboardStats",
    "ProgramStats",
]
