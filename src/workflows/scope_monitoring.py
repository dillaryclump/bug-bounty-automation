"""
Scope Monitoring Workflows
Prefect workflows for monitoring bug bounty program scope changes.
"""

from datetime import datetime
from typing import Dict, List, Optional

from prefect import flow, task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_session
from src.db.models import Program, ScopeHistory, ScopeChangeType
from src.scope import (
    ScopeParserFactory,
    ScopeData,
    ScopeComparator,
    ScopeValidator,
)
from src.alerting.manager import AlertManager
from src.utils.logging import get_logger

logger = get_logger(__name__)


@task(name="fetch_program_scope", retries=2)
async def fetch_program_scope_task(
    program_id: int,
    platform: str,
    handle: str,
    api_token: Optional[str] = None,
) -> ScopeData:
    """
    Fetch current scope for a program.
    
    Args:
        program_id: Program database ID
        platform: Platform name (hackerone, bugcrowd, etc.)
        handle: Program handle
        api_token: Optional API token
        
    Returns:
        ScopeData with current scope
    """
    logger.info(f"Fetching scope for program {program_id} ({platform}/{handle})")
    
    # Get parser
    async with ScopeParserFactory.create(platform, api_token=api_token) as parser:
        scope_data = await parser.fetch_scope(handle)
    
    logger.info(
        f"Fetched scope: {len(scope_data.in_scope)} in-scope, "
        f"{len(scope_data.out_of_scope)} out-of-scope"
    )
    
    return scope_data


@task(name="get_previous_scope")
async def get_previous_scope_task(program_id: int) -> Optional[ScopeData]:
    """
    Get the most recent scope snapshot for comparison.
    
    Args:
        program_id: Program ID
        
    Returns:
        ScopeData if previous snapshot exists, else None
    """
    logger.info(f"Fetching previous scope for program {program_id}")
    
    async with get_session() as session:
        result = await session.execute(
            select(ScopeHistory)
            .where(ScopeHistory.program_id == program_id)
            .order_by(ScopeHistory.checked_at.desc())
            .limit(1)
        )
        
        history = result.scalar_one_or_none()
        
        if not history:
            logger.info("No previous scope found")
            return None
        
        # Get program for metadata
        program_result = await session.execute(
            select(Program).where(Program.id == program_id)
        )
        program = program_result.scalar_one()
        
        # Reconstruct ScopeData
        scope_data = ScopeData(
            in_scope=history.in_scope or [],
            out_of_scope=history.out_of_scope or [],
            platform=program.platform,
            program_handle=program.handle,
            program_name=program.name,
            program_url=program.url or "",
        )
        
        logger.info(
            f"Found previous scope from {history.checked_at}: "
            f"{len(scope_data.in_scope)} in-scope, "
            f"{len(scope_data.out_of_scope)} out-of-scope"
        )
        
        return scope_data


@task(name="compare_scope")
async def compare_scope_task(
    previous: Optional[ScopeData],
    current: ScopeData,
) -> Dict:
    """
    Compare scope snapshots.
    
    Args:
        previous: Previous scope (or None if first check)
        current: Current scope
        
    Returns:
        Dict with comparison results
    """
    if not previous:
        logger.info("First scope check - no comparison")
        return {
            "has_changes": True,  # Treat first check as change
            "is_first_check": True,
            "additions": len(current.in_scope) + len(current.out_of_scope),
            "removals": 0,
            "modifications": 0,
            "summary": "First scope check",
        }
    
    logger.info("Comparing scope snapshots")
    
    comparator = ScopeComparator()
    comparison = comparator.compare(previous, current)
    
    logger.info(f"Comparison: {comparison.summary()}")
    
    return {
        "has_changes": comparison.has_changes,
        "is_first_check": False,
        "additions": len(comparison.additions),
        "removals": len(comparison.removals),
        "modifications": len(comparison.modifications),
        "summary": comparison.summary(),
        "changes": [
            {
                "type": change.change_type.value,
                "item": change.item,
                "category": change.category,
                "details": change.details,
            }
            for change in comparison.changes
        ],
    }


@task(name="save_scope_snapshot")
async def save_scope_snapshot_task(
    program_id: int,
    scope_data: ScopeData,
    changes: Dict,
    source: str = "api",
) -> int:
    """
    Save scope snapshot to database.
    
    Args:
        program_id: Program ID
        scope_data: Current scope data
        changes: Comparison results
        source: How scope was obtained (api/web_scrape/manual)
        
    Returns:
        ScopeHistory ID
    """
    logger.info(f"Saving scope snapshot for program {program_id}")
    
    async with get_session() as session:
        # Create scope history record
        history = ScopeHistory(
            program_id=program_id,
            in_scope=scope_data.in_scope,
            out_of_scope=scope_data.out_of_scope,
            changes=changes.get("changes", []),
            checksum=scope_data.checksum(),
            source=source,
        )
        
        session.add(history)
        await session.commit()
        await session.refresh(history)
        
        logger.info(f"Saved scope snapshot: {history.id}")
        
        return history.id


@task(name="validate_program_assets")
async def validate_program_assets_task(
    program_id: int,
    scope_data: ScopeData,
) -> Dict:
    """
    Validate all program assets against current scope.
    
    Args:
        program_id: Program ID
        scope_data: Current scope
        
    Returns:
        Dict with validation results
    """
    logger.info(f"Validating assets for program {program_id}")
    
    validator = ScopeValidator(scope_data)
    
    async with get_session() as session:
        # Get all assets for this program
        from src.db.models import Asset
        
        result = await session.execute(
            select(Asset)
            .where(Asset.program_id == program_id)
            .where(Asset.is_alive == True)
        )
        
        assets = result.scalars().all()
        
        if not assets:
            logger.info("No assets to validate")
            return {
                "total": 0,
                "in_scope": 0,
                "out_scope": 0,
            }
        
        # Validate each asset
        in_scope_count = 0
        out_scope_count = 0
        
        for asset in assets:
            validation = validator.validate(asset.value)
            
            # Update asset scope status if changed
            if asset.in_scope != validation.in_scope:
                logger.info(
                    f"Asset scope changed: {asset.value} "
                    f"({asset.in_scope} -> {validation.in_scope})"
                )
                asset.in_scope = validation.in_scope
            
            if validation.in_scope:
                in_scope_count += 1
            else:
                out_scope_count += 1
        
        await session.commit()
        
        logger.info(
            f"Validated {len(assets)} assets: "
            f"{in_scope_count} in-scope, {out_scope_count} out-of-scope"
        )
        
        return {
            "total": len(assets),
            "in_scope": in_scope_count,
            "out_scope": out_scope_count,
        }


@task(name="send_scope_change_alert")
async def send_scope_change_alert_task(
    program_id: int,
    scope_history_id: int,
    changes_summary: Dict,
) -> bool:
    """
    Send alert for scope changes.
    
    Args:
        program_id: Program ID
        scope_history_id: Scope history record ID
        changes_summary: Changes summary dict
        
    Returns:
        True if alert sent successfully
    """
    logger.info(f"Sending scope change alert for program {program_id}")
    
    async with get_session() as session:
        # Get program
        program_result = await session.execute(
            select(Program).where(Program.id == program_id)
        )
        program = program_result.scalar_one_or_none()
        
        if not program:
            logger.error(f"Program {program_id} not found")
            return False
        
        # Get scope history
        scope_history = await session.get(ScopeHistory, scope_history_id)
        
        if not scope_history:
            logger.error(f"Scope history {scope_history_id} not found")
            return False
        
        # Send alert
        async with AlertManager(session) as alert_manager:
            success = await alert_manager.alert_scope_change(
                program=program,
                scope_history=scope_history,
                changes_summary=changes_summary,
            )
        
        logger.info(f"Scope change alert sent: {success}")
        return success


@flow(name="Monitor Program Scope")
async def monitor_program_scope_flow(
    program_id: int,
    api_token: Optional[str] = None,
) -> Dict:
    """
    Monitor a single program's scope for changes.
    
    Args:
        program_id: Program ID
        api_token: Optional API token for platform
        
    Returns:
        Dict with monitoring results
    """
    logger.info(f"Starting scope monitoring for program {program_id}")
    
    # Get program info
    async with get_session() as session:
        result = await session.execute(
            select(Program).where(Program.id == program_id)
        )
        program = result.scalar_one_or_none()
        
        if not program:
            logger.error(f"Program {program_id} not found")
            return {"error": "Program not found"}
    
    # Fetch current scope
    current_scope = await fetch_program_scope_task(
        program_id=program_id,
        platform=program.platform,
        handle=program.handle,
        api_token=api_token,
    )
    
    # Get previous scope
    previous_scope = await get_previous_scope_task(program_id)
    
    # Compare
    comparison = await compare_scope_task(previous_scope, current_scope)
    
    # Save snapshot
    history_id = await save_scope_snapshot_task(
        program_id=program_id,
        scope_data=current_scope,
        changes=comparison,
        source="api" if api_token else "web_scrape",
    )
    
    # Send alert if scope changed
    alert_sent = False
    if comparison["has_changes"]:
        alert_sent = await send_scope_change_alert_task(
            program_id=program_id,
            scope_history_id=history_id,
            changes_summary=comparison,
        )
    
    # Validate assets if scope changed
    validation_results = None
    if comparison["has_changes"]:
        validation_results = await validate_program_assets_task(
            program_id=program_id,
            scope_data=current_scope,
        )
    
    logger.info(f"Scope monitoring complete for program {program_id}")
    
    return {
        "program_id": program_id,
        "program_name": program.name,
        "history_id": history_id,
        "comparison": comparison,
        "validation": validation_results,
        "current_scope": {
            "in_scope_count": len(current_scope.in_scope),
            "out_scope_count": len(current_scope.out_of_scope),
            "checksum": current_scope.checksum()[:8],
        },
    }


@flow(name="Monitor All Programs Scope")
async def monitor_all_programs_scope_flow(
    platform: Optional[str] = None,
    api_token: Optional[str] = None,
) -> Dict:
    """
    Monitor scope for all active programs.
    
    Args:
        platform: Optional filter by platform
        api_token: Optional API token
        
    Returns:
        Dict with results for all programs
    """
    logger.info("Starting scope monitoring for all programs")
    
    # Get all active programs
    async with get_session() as session:
        query = select(Program).where(Program.is_active == True)
        
        if platform:
            query = query.where(Program.platform == platform)
        
        result = await session.execute(query)
        programs = result.scalars().all()
    
    if not programs:
        logger.info("No active programs found")
        return {"programs": []}
    
    logger.info(f"Monitoring {len(programs)} programs")
    
    # Monitor each program
    results = []
    for program in programs:
        try:
            result = await monitor_program_scope_flow(
                program_id=program.id,
                api_token=api_token,
            )
            results.append(result)
        except Exception as e:
            logger.error(f"Error monitoring program {program.id}: {e}")
            results.append({
                "program_id": program.id,
                "program_name": program.name,
                "error": str(e),
            })
    
    # Summary
    total_changes = sum(
        1 for r in results
        if r.get("comparison", {}).get("has_changes")
    )
    
    logger.info(
        f"Scope monitoring complete: {len(results)} programs checked, "
        f"{total_changes} with changes"
    )
    
    return {
        "total_programs": len(results),
        "programs_with_changes": total_changes,
        "programs": results,
    }
