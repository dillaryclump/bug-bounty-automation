"""
Bulk operations endpoints

Perform batch operations on multiple resources.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from src.api.dependencies.database import get_db
from src.api.dependencies.auth import require_user_or_admin
from src.db.repositories.asset_repository import AssetRepository
from src.db.repositories.vulnerability_repository import VulnerabilityRepository
from src.db.repositories.program_repository import ProgramRepository
from src.db.models import User


router = APIRouter(prefix="/bulk", tags=["Bulk Operations"])


class BulkDeleteRequest(BaseModel):
    """Request schema for bulk deletion."""
    ids: list[int]


class BulkUpdateStatusRequest(BaseModel):
    """Request schema for bulk status update."""
    ids: list[int]
    is_active: bool


class BulkMarkReportedRequest(BaseModel):
    """Request schema for bulk marking vulnerabilities as reported."""
    ids: list[int]


class BulkScopeUpdateRequest(BaseModel):
    """Request schema for bulk scope update."""
    ids: list[int]
    in_scope: bool


@router.post("/vulnerabilities/mark-reported")
async def bulk_mark_vulns_reported(
    request: BulkMarkReportedRequest,
    current_user: User = Depends(require_user_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Mark multiple vulnerabilities as reported in one operation.
    
    Limit: 1000 vulnerabilities per request
    """
    if len(request.ids) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process more than 1000 vulnerabilities at once"
        )
    
    repo = VulnerabilityRepository(db)
    
    updated_count = 0
    for vuln_id in request.ids:
        vuln = await repo.get_by_id(vuln_id)
        if vuln and not vuln.is_reported:
            await repo.mark_as_reported(vuln_id)
            updated_count += 1
    
    return {
        "success": True,
        "message": f"Marked {updated_count} vulnerabilities as reported",
        "updated_count": updated_count,
        "total_requested": len(request.ids)
    }


@router.delete("/vulnerabilities")
async def bulk_delete_vulnerabilities(
    request: BulkDeleteRequest,
    current_user: User = Depends(require_user_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete multiple vulnerabilities in one operation.
    
    Limit: 1000 vulnerabilities per request
    """
    if len(request.ids) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete more than 1000 vulnerabilities at once"
        )
    
    repo = VulnerabilityRepository(db)
    
    deleted_count = 0
    for vuln_id in request.ids:
        vuln = await repo.get_by_id(vuln_id)
        if vuln:
            await repo.delete(vuln)
            deleted_count += 1
    
    return {
        "success": True,
        "message": f"Deleted {deleted_count} vulnerabilities",
        "deleted_count": deleted_count,
        "total_requested": len(request.ids)
    }


@router.post("/assets/scope")
async def bulk_update_asset_scope(
    request: BulkScopeUpdateRequest,
    current_user: User = Depends(require_user_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update scope status for multiple assets in one operation.
    
    Limit: 1000 assets per request
    """
    if len(request.ids) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process more than 1000 assets at once"
        )
    
    repo = AssetRepository(db)
    
    updated_count = 0
    for asset_id in request.ids:
        asset = await repo.get_by_id(asset_id)
        if asset:
            asset.in_scope = request.in_scope
            await repo.update(asset)
            updated_count += 1
    
    return {
        "success": True,
        "message": f"Updated scope for {updated_count} assets",
        "updated_count": updated_count,
        "total_requested": len(request.ids),
        "in_scope": request.in_scope
    }


@router.delete("/assets")
async def bulk_delete_assets(
    request: BulkDeleteRequest,
    current_user: User = Depends(require_user_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete multiple assets in one operation.
    
    Limit: 1000 assets per request
    Warning: This will also delete associated vulnerabilities and ports.
    """
    if len(request.ids) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete more than 1000 assets at once"
        )
    
    repo = AssetRepository(db)
    
    deleted_count = 0
    for asset_id in request.ids:
        asset = await repo.get_by_id(asset_id)
        if asset:
            await repo.delete(asset)
            deleted_count += 1
    
    return {
        "success": True,
        "message": f"Deleted {deleted_count} assets (and associated data)",
        "deleted_count": deleted_count,
        "total_requested": len(request.ids)
    }


@router.post("/programs/status")
async def bulk_update_program_status(
    request: BulkUpdateStatusRequest,
    current_user: User = Depends(require_user_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Activate or deactivate multiple programs in one operation.
    
    Limit: 100 programs per request
    """
    if len(request.ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot process more than 100 programs at once"
        )
    
    repo = ProgramRepository(db)
    
    updated_count = 0
    for program_id in request.ids:
        program = await repo.get_by_id(program_id)
        if program:
            program.is_active = request.is_active
            await repo.update(program)
            updated_count += 1
    
    return {
        "success": True,
        "message": f"Updated status for {updated_count} programs",
        "updated_count": updated_count,
        "total_requested": len(request.ids),
        "is_active": request.is_active
    }


@router.delete("/programs")
async def bulk_delete_programs(
    request: BulkDeleteRequest,
    current_user: User = Depends(require_user_or_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete multiple programs in one operation.
    
    Limit: 100 programs per request
    Warning: This will cascade delete all associated data (assets, vulnerabilities, scans, etc.)
    """
    if len(request.ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete more than 100 programs at once"
        )
    
    repo = ProgramRepository(db)
    
    deleted_count = 0
    for program_id in request.ids:
        program = await repo.get_by_id(program_id)
        if program:
            await repo.delete(program)
            deleted_count += 1
    
    return {
        "success": True,
        "message": f"Deleted {deleted_count} programs (and all associated data)",
        "deleted_count": deleted_count,
        "total_requested": len(request.ids),
        "warning": "This operation has cascaded to delete all associated assets, vulnerabilities, scans, etc."
    }
