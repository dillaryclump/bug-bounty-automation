"""
Vulnerability API Routes
Endpoints for managing vulnerabilities.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas.vulnerabilities import (
    VulnerabilityResponse,
    VulnerabilityListResponse,
    VulnerabilityMarkReported,
)
from src.db.models import Vulnerability, Asset, Program, SeverityLevel
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=VulnerabilityListResponse)
async def list_vulnerabilities(
    program_id: Optional[int] = Query(None, description="Filter by program ID"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    is_reported: Optional[bool] = Query(None, description="Filter by reported status"),
    new_only: bool = Query(False, description="Only show unreported vulnerabilities"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List all vulnerabilities with optional filtering."""
    # Build query
    query = select(Vulnerability)
    filters = []
    
    if program_id:
        filters.append(Vulnerability.program_id == program_id)
    if severity:
        filters.append(Vulnerability.severity == severity)
    if is_reported is not None:
        filters.append(Vulnerability.is_reported == is_reported)
    if new_only:
        filters.append(Vulnerability.is_reported == False)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get vulnerabilities with pagination
    query = query.offset(skip).limit(limit).order_by(Vulnerability.discovered_at.desc())
    result = await db.execute(query)
    vulnerabilities = result.scalars().all()
    
    # Enrich with asset and program details
    vulns_with_details = []
    for vuln in vulnerabilities:
        # Get asset
        asset = await db.get(Asset, vuln.asset_id)
        # Get program
        program = await db.get(Program, vuln.program_id)
        
        vuln_dict = {
            **{c.name: getattr(vuln, c.name) for c in Vulnerability.__table__.columns},
            "asset_value": asset.value if asset else None,
            "asset_type": asset.asset_type if asset else None,
            "program_name": program.name if program else None,
            "platform": program.platform if program else None,
        }
        vulns_with_details.append(VulnerabilityResponse(**vuln_dict))
    
    # Get severity counts
    severity_counts = {}
    for sev in ["critical", "high", "medium", "low", "info"]:
        count_result = await db.execute(
            select(func.count(Vulnerability.id)).where(
                and_(
                    *([f for f in filters if f.left.name != "severity"]),  # Exclude severity filter
                    Vulnerability.severity == sev,
                )
            ) if filters else select(func.count(Vulnerability.id)).where(Vulnerability.severity == sev)
        )
        severity_counts[sev] = count_result.scalar() or 0
    
    return VulnerabilityListResponse(
        total=total,
        vulnerabilities=vulns_with_details,
        severity_counts=severity_counts,
        filters={
            "program_id": program_id,
            "severity": severity,
            "is_reported": is_reported,
            "new_only": new_only,
        },
    )


@router.get("/{vuln_id}", response_model=VulnerabilityResponse)
async def get_vulnerability(
    vuln_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific vulnerability by ID."""
    vuln = await db.get(Vulnerability, vuln_id)
    if not vuln:
        raise HTTPException(status_code=404, detail="Vulnerability not found")
    
    # Get asset and program
    asset = await db.get(Asset, vuln.asset_id)
    program = await db.get(Program, vuln.program_id)
    
    vuln_dict = {
        **{c.name: getattr(vuln, c.name) for c in Vulnerability.__table__.columns},
        "asset_value": asset.value if asset else None,
        "asset_type": asset.asset_type if asset else None,
        "program_name": program.name if program else None,
        "platform": program.platform if program else None,
    }
    
    return VulnerabilityResponse(**vuln_dict)


@router.post("/mark-reported", status_code=200)
async def mark_reported(
    data: VulnerabilityMarkReported,
    db: AsyncSession = Depends(get_db),
):
    """Mark vulnerabilities as reported."""
    from datetime import datetime
    
    updated_count = 0
    for vuln_id in data.vulnerability_ids:
        vuln = await db.get(Vulnerability, vuln_id)
        if vuln:
            vuln.is_reported = True
            vuln.reported_at = datetime.utcnow()
            updated_count += 1
    
    await db.commit()
    
    logger.info(f"Marked {updated_count} vulnerabilities as reported")
    
    return {
        "success": True,
        "updated_count": updated_count,
        "message": f"Marked {updated_count} vulnerabilities as reported",
    }
