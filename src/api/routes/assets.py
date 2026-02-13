"""
Asset API Routes
Endpoints for managing discovered assets.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.api.dependencies import get_db
from src.api.schemas.assets import AssetResponse, AssetListResponse
from src.db.models import Asset, Vulnerability
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=AssetListResponse)
async def list_assets(
    program_id: Optional[int] = Query(None, description="Filter by program ID"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type"),
    is_alive: Optional[bool] = Query(None, description="Filter by alive status"),
    in_scope: Optional[bool] = Query(None, description="Filter by scope status"),
    has_vulnerabilities: Optional[bool] = Query(None, description="Filter assets with vulnerabilities"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List all assets with optional filtering."""
    # Build query
    query = select(Asset)
    filters = []
    
    if program_id:
        filters.append(Asset.program_id == program_id)
    if asset_type:
        filters.append(Asset.asset_type == asset_type)
    if is_alive is not None:
        filters.append(Asset.is_alive == is_alive)
    if in_scope is not None:
        filters.append(Asset.in_scope == in_scope)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query =select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get assets with pagination
    query = query.offset(skip).limit(limit).order_by(Asset.discovered_at.desc())
    result = await db.execute(query)
    assets = result.scalars().all()
    
    # Enrich with vulnerability counts
    assets_with_stats = []
    for asset in assets:
        vuln_count_result = await db.execute(
            select(func.count(Vulnerability.id)).where(Vulnerability.asset_id == asset.id)
        )
        vuln_count = vuln_count_result.scalar() or 0
        
        critical_count_result = await db.execute(
            select(func.count(Vulnerability.id)).where(
                Vulnerability.asset_id == asset.id,
                Vulnerability.severity == "critical",
            )
        )
        critical_count = critical_count_result.scalar() or 0
        
        asset_dict = {
            **{c.name: getattr(asset, c.name) for c in Asset.__table__.columns},
            "vuln_count": vuln_count,
            "critical_vuln_count": critical_count,
        }
        assets_with_stats.append(AssetResponse(**asset_dict))
    
    return AssetListResponse(
        total=total,
        assets=assets_with_stats,
        filters={
            "program_id": program_id,
            "asset_type": asset_type,
            "is_alive": is_alive,
            "in_scope": in_scope,
        },
    )


@router.get("/{asset_id}", response_model=AssetResponse)
async def get_asset(
    asset_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific asset by ID."""
    asset = await db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Get vulnerability counts
    vuln_count_result = await db.execute(
        select(func.count(Vulnerability.id)).where(Vulnerability.asset_id == asset_id)
    )
    vuln_count = vuln_count_result.scalar() or 0
    
    critical_count_result = await db.execute(
        select(func.count(Vulnerability.id)).where(
            Vulnerability.asset_id == asset_id,
            Vulnerability.severity == "critical",
        )
    )
    critical_count = critical_count_result.scalar() or 0
    
    asset_dict = {
        **{c.name: getattr(asset, c.name) for c in Asset.__table__.columns},
        "vuln_count": vuln_count,
        "critical_vuln_count": critical_count,
    }
    
    return AssetResponse(**asset_dict)
