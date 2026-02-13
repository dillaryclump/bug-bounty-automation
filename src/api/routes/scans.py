"""
Scan API Routes  
Endpoints for managing and triggering scans.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas.scans import (
    ScanResponse,
    ScanListResponse,
    ScanCreateRequest,
    ScanStatus,
)
from src.db.models import Program, Scan
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=ScanListResponse)
async def list_scans(
    program_id: Optional[int] = Query(None, description="Filter by program ID"),
    status: Optional[ScanStatus] = Query(None, description="Filter by status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List all scans with optional filtering."""
    # Build query
    query = select(Scan)
    
    if program_id:
        query = query.where(Scan.program_id == program_id)
    if status:
        query = query.where(Scan.status == status.value)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get scans with pagination
    query = query.offset(skip).limit(limit).order_by(Scan.created_at.desc())
    result = await db.execute(query)
    scans = result.scalars().all()
    
    # Enrich with program details
    scans_with_details = []
    for scan in scans:
        program = await db.get(Program, scan.program_id)
        
        scan_dict = {
            **{c.name: getattr(scan, c.name) for c in Scan.__table__.columns},
            "program_name": program.name if program else None,
        }
        scans_with_details.append(ScanResponse(**scan_dict))
    
    return ScanListResponse(
        total=total,
        scans=scans_with_details,
    )


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific scan by ID."""
    scan = await db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    
    program = await db.get(Program, scan.program_id)
    
    scan_dict = {
        **{c.name: getattr(scan, c.name) for c in Scan.__table__.columns},
        "program_name": program.name if program else None,
    }
    
    return ScanResponse(**scan_dict)


@router.post("", response_model=dict, status_code=202)
async def create_scan(
    scan_data: ScanCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Trigger a new scan.
    
    Returns immediately with scan details.
    Actual scanning happens in background.
    """
    # Verify program exists
    program = await db.get(Program, scan_data.program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Create scan record
    scan = Scan(
        program_id=scan_data.program_id,
        scan_type=scan_data.scan_type.value,
        status="pending",
    )
    db.add(scan)
    await db.commit()
    await db.refresh(scan)
    
    # Schedule scan in background
    async def run_scan():
        """Run scan in background."""
        try:
            if scan_data.scan_type.value == "recon_full":
                from src.workflows.reconnaissance import full_reconnaissance_flow
                await full_reconnaissance_flow(scan_data.program_id)
            elif scan_data.scan_type.value == "recon_quick":
                from src.workflows.reconnaissance import quick_reconnaissance_flow
                await quick_reconnaissance_flow(scan_data.program_id)
            elif scan_data.scan_type.value == "vuln_scan":
                from src.workflows.vulnerability_scan import vulnerability_scan_flow
                await vulnerability_scan_flow(
                    scan_data.program_id,
                    force_rescan=scan_data.force,
                )
            elif scan_data.scan_type.value == "scope_check":
                from src.workflows.scope_monitoring import monitor_program_scope_flow
                await monitor_program_scope_flow(scan_data.program_id)
                
            logger.info(f"Scan {scan.id} completed successfully")
        except Exception as e:
            logger.error(f"Scan {scan.id} failed: {e}")
    
    background_tasks.add_task(run_scan)
    
    logger.info(f"Triggered {scan_data.scan_type.value} scan for program {program.name}")
    
    return {
        "success": True,
        "scan_id": scan.id,
        "message": f"Scan triggered successfully",
        "status": "pending",
    }
