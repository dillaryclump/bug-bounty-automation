"""
Scope API Routes
Endpoints for scope monitoring.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas.scope import (
    ScopeHistoryResponse,
    ScopeHistoryListResponse,
    ScopeCheckRequest,
    ScopeValidationResponse,
    ScopeValidationListResponse,
)
from src.db.models import Program, ScopeHistory, Asset
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/history", response_model=ScopeHistoryListResponse)
async def list_scope_history(
    program_id: int = Query(..., description="Program ID"),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Get scope history for a program."""
    # Verify program exists
    program = await db.get(Program, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Get scope history
    query = (
        select(ScopeHistory)
        .where(ScopeHistory.program_id == program_id)
        .order_by(ScopeHistory.checked_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    history = result.scalars().all()
    
    # Add change counts
    history_with_counts = []
    for entry in history:
        changes = entry.changes or []
        additions = sum(1 for c in changes if c.get("type") == "added")
        removals = sum(1 for c in changes if c.get("type") == "removed")
        modifications = sum(1 for c in changes if c.get("type") == "modified")
        
        entry_dict = {
            **{c.name: getattr(entry, c.name) for c in ScopeHistory.__table__.columns},
            "additions": additions,
            "removals": removals,
            "modifications": modifications,
        }
        history_with_counts.append(ScopeHistoryResponse(**entry_dict))
    
    return ScopeHistoryListResponse(
        total=len(history_with_counts),
        history=history_with_counts,
    )


@router.post("/check", status_code=202)
async def check_scope(
    scope_check: ScopeCheckRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a scope check for a program."""
    # Verify program exists
    program = await db.get(Program, scope_check.program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Schedule scope check in background
    async def run_scope_check():
        """Run scope check in background."""
        try:
            from src.workflows.scope_monitoring import monitor_program_scope_flow
            result = await monitor_program_scope_flow(
                program_id=scope_check.program_id,
                api_token=scope_check.api_token,
            )
            logger.info(f"Scope check completed for program {scope_check.program_id}")
            return result
        except Exception as e:
            logger.error(f"Scope check failed for program {scope_check.program_id}: {e}")
            raise
    
    background_tasks.add_task(run_scope_check)
    
    return {
        "success": True,
        "message": f"Scope check triggered for program {program.name}",
        "program_id": scope_check.program_id,
    }


@router.post("/validate", response_model=ScopeValidationListResponse)
async def validate_assets(
    program_id: int = Query(..., description="Program ID"),
    db: AsyncSession = Depends(get_db),
):
    """Validate all assets against current program scope."""
    # Verify program exists
    program = await db.get(Program, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Get latest scope
    scope_result = await db.execute(
        select(ScopeHistory)
        .where(ScopeHistory.program_id == program_id)
        .order_by(ScopeHistory.checked_at.desc())
        .limit(1)
    )
    scope_history = scope_result.scalar_one_or_none()
    
    if not scope_history:
        raise HTTPException(
            status_code=404,
            detail="No scope history found - run scope check first",
        )
    
    # Create scope data
    from src.scope import ScopeData, ScopeValidator
    
    scope_data = ScopeData(
        in_scope=scope_history.in_scope or [],
        out_of_scope=scope_history.out_of_scope or [],
        platform=program.platform,
        program_handle=program.handle,
        program_name=program.name,
        program_url=program.url or "",
    )
    
    # Get all assets
    assets_result = await db.execute(
        select(Asset).where(
            Asset.program_id == program_id,
            Asset.is_alive == True,
        )
    )
    assets = assets_result.scalars().all()
    
    if not assets:
        return ScopeValidationListResponse(
            total=0,
            in_scope_count=0,
            out_scope_count=0,
            results=[],
        )
    
    # Validate assets
    validator = ScopeValidator(scope_data)
    
    results = []
    in_scope_count = 0
    out_scope_count = 0
    
    for asset in assets:
        validation = validator.validate(asset.value)
        
        results.append(ScopeValidationResponse(
            asset=asset.value,
            in_scope=validation.in_scope,
            reason=validation.reason,
            matched_rule=validation.matched_rule,
        ))
        
        if validation.in_scope:
            in_scope_count += 1
        else:
            out_scope_count += 1
    
    return ScopeValidationListResponse(
        total=len(results),
        in_scope_count=in_scope_count,
        out_scope_count=out_scope_count,
        results=results,
    )
