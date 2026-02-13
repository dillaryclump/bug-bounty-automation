"""
Program API Routes
Endpoints for managing bug bounty programs.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas.programs import (
    ProgramCreate,
    ProgramUpdate,
    ProgramResponse,
    ProgramListResponse,
)
from src.db.models import Program, Asset, Vulnerability, SeverityLevel
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=ProgramListResponse)
async def list_programs(
    platform: Optional[str] = Query(None, description="Filter by platform"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List all programs with optional filtering."""
    # Build query
    query = select(Program)
    
    if platform:
        query = query.where(Program.platform == platform)
    if is_active is not None:
        query = query.where(Program.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get programs with pagination
    query = query.offset(skip).limit(limit).order_by(Program.created_at.desc())
    result = await db.execute(query)
    programs = result.scalars().all()
    
    # Enrich with stats
    programs_with_stats = []
    for program in programs:
        # Count assets
        asset_count_query = select(func.count(Asset.id)).where(
            Asset.program_id == program.id
        )
        asset_count_result = await db.execute(asset_count_query)
        asset_count = asset_count_result.scalar() or 0
        
        # Count vulnerabilities
        vuln_count_query = select(func.count(Vulnerability.id)).where(
            Vulnerability.program_id == program.id
        )
        vuln_count_result = await db.execute(vuln_count_query)
        vuln_count = vuln_count_result.scalar() or 0
        
        # Count critical vulnerabilities
        critical_count_query = select(func.count(Vulnerability.id)).where(
            Vulnerability.program_id == program.id,
            Vulnerability.severity == SeverityLevel.CRITICAL,
        )
        critical_count_result = await db.execute(critical_count_query)
        critical_count = critical_count_result.scalar() or 0
        
        # Create response with stats
        program_dict = {
            **{c.name: getattr(program, c.name) for c in Program.__table__.columns},
            "asset_count": asset_count,
            "vuln_count": vuln_count,
            "critical_vuln_count": critical_count,
        }
        programs_with_stats.append(ProgramResponse(**program_dict))
    
    return ProgramListResponse(
        total=total,
        programs=programs_with_stats,
    )


@router.post("", response_model=ProgramResponse, status_code=201)
async def create_program(
    program_data: ProgramCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new program."""
    # Check if program already exists
    existing = await db.execute(
        select(Program).where(
            Program.platform == program_data.platform,
            Program.handle == program_data.handle,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"Program {program_data.handle} already exists on {program_data.platform}",
        )
    
    # Create program
    program = Program(**program_data.model_dump())
    db.add(program)
    await db.commit()
    await db.refresh(program)
    
    logger.info(f"Created program: {program.name} ({program.platform}/{program.handle})")
    
    return ProgramResponse.model_validate(program)


@router.get("/{program_id}", response_model=ProgramResponse)
async def get_program(
    program_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific program by ID."""
    program = await db.get(Program, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Get stats
    asset_count_result = await db.execute(
        select(func.count(Asset.id)).where(Asset.program_id == program_id)
    )
    asset_count = asset_count_result.scalar() or 0
    
    vuln_count_result = await db.execute(
        select(func.count(Vulnerability.id)).where(Vulnerability.program_id == program_id)
    )
    vuln_count = vuln_count_result.scalar() or 0
    
    critical_count_result = await db.execute(
        select(func.count(Vulnerability.id)).where(
            Vulnerability.program_id == program_id,
            Vulnerability.severity == SeverityLevel.CRITICAL,
        )
    )
    critical_count = critical_count_result.scalar() or 0
    
    program_dict = {
        **{c.name: getattr(program, c.name) for c in Program.__table__.columns},
        "asset_count": asset_count,
        "vuln_count": vuln_count,
        "critical_vuln_count": critical_count,
    }
    
    return ProgramResponse(**program_dict)


@router.patch("/{program_id}", response_model=ProgramResponse)
async def update_program(
    program_id: int,
    program_data: ProgramUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a program."""
    program = await db.get(Program, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Update fields
    update_data = program_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(program, field, value)
    
    await db.commit()
    await db.refresh(program)
    
    logger.info(f"Updated program: {program.name}")
    
    return ProgramResponse.model_validate(program)


@router.delete("/{program_id}", status_code=204)
async def delete_program(
    program_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Delete a program."""
    program = await db.get(Program, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    await db.delete(program)
    await db.commit()
    
    logger.info(f"Deleted program: {program.name}")
    
    return None
