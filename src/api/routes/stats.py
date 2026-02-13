"""
Statistics API Routes
Endpoints for dashboard statistics.
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas.stats import (
    DashboardStats,
    ProgramStats,
    TimeSeriesResponse,
    TimeSeriesDataPoint,
)
from src.db.models import (
    Program,
    Asset,
    Vulnerability,
    Scan,
    Alert,
    ScopeHistory,
    SeverityLevel,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard statistics."""
    now = datetime.utcnow()
    yesterday = now - timedelta(hours=24)
    
    # Programs
    total_programs_result = await db.execute(select(func.count(Program.id)))
    total_programs = total_programs_result.scalar() or 0
    
    active_programs_result = await db.execute(
        select(func.count(Program.id)).where(Program.is_active == True)
    )
    active_programs = active_programs_result.scalar() or 0
    
    # Assets
    total_assets_result = await db.execute(select(func.count(Asset.id)))
    total_assets = total_assets_result.scalar() or 0
    
    alive_assets_result = await db.execute(
        select(func.count(Asset.id)).where(Asset.is_alive == True)
    )
    alive_assets = alive_assets_result.scalar() or 0
    
    in_scope_assets_result = await db.execute(
        select(func.count(Asset.id)).where(Asset.in_scope == True, Asset.is_alive == True)
    )
    in_scope_assets = in_scope_assets_result.scalar() or 0
    
    new_assets_24h_result = await db.execute(
        select(func.count(Asset.id)).where(Asset.discovered_at >= yesterday)
    )
    new_assets_24h = new_assets_24h_result.scalar() or 0
    
    # Vulnerabilities
    total_vulns_result = await db.execute(select(func.count(Vulnerability.id)))
    total_vulnerabilities = total_vulns_result.scalar() or 0
    
    new_vulns_24h_result = await db.execute(
        select(func.count(Vulnerability.id)).where(Vulnerability.discovered_at >= yesterday)
    )
    new_vulnerabilities_24h = new_vulns_24h_result.scalar() or 0
    
    # Vulnerability counts by severity
    severity_counts = {}
    for severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW, SeverityLevel.INFO]:
        count_result = await db.execute(
            select(func.count(Vulnerability.id)).where(Vulnerability.severity == severity)
        )
        severity_counts[severity.value] = count_result.scalar() or 0
    
    unreported_result = await db.execute(
        select(func.count(Vulnerability.id)).where(Vulnerability.is_reported == False)
    )
    unreported_count = unreported_result.scalar() or 0
    
    # Scans
    total_scans_result = await db.execute(select(func.count(Scan.id)))
    total_scans = total_scans_result.scalar() or 0
    
    scans_24h_result = await db.execute(
        select(func.count(Scan.id)).where(Scan.created_at >= yesterday)
    )
    scans_24h = scans_24h_result.scalar() or 0
    
    running_scans_result = await db.execute(
        select(func.count(Scan.id)).where(Scan.status == "running")
    )
    running_scans = running_scans_result.scalar() or 0
    
    # Alerts
    alerts_24h_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.created_at >= yesterday, Alert.sent == True)
    )
    alerts_sent_24h = alerts_24h_result.scalar() or 0
    
    failed_alerts_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.sent == True, Alert.success == False)
    )
    failed_alerts = failed_alerts_result.scalar() or 0
    
    # Scope changes
    scope_changes_24h_result = await db.execute(
        select(func.count(ScopeHistory.id)).where(ScopeHistory.checked_at >= yesterday)
    )
    scope_changes_24h = scope_changes_24h_result.scalar() or 0
    
    # Recent activity
    last_scan_result = await db.execute(
        select(Scan.created_at).order_by(Scan.created_at.desc()).limit(1)
    )
    last_scan = last_scan_result.scalar_one_or_none()
    
    last_vuln_result = await db.execute(
        select(Vulnerability.discovered_at).order_by(Vulnerability.discovered_at.desc()).limit(1)
    )
    last_vulnerability = last_vuln_result.scalar_one_or_none()
    
    last_scope_result = await db.execute(
        select(ScopeHistory.checked_at).order_by(ScopeHistory.checked_at.desc()).limit(1)
    )
    last_scope_check = last_scope_result.scalar_one_or_none()
    
    return DashboardStats(
        total_programs=total_programs,
        active_programs=active_programs,
        total_assets=total_assets,
        alive_assets=alive_assets,
        in_scope_assets=in_scope_assets,
        new_assets_24h=new_assets_24h,
        total_vulnerabilities=total_vulnerabilities,
        new_vulnerabilities_24h=new_vulnerabilities_24h,
        critical_count=severity_counts.get("critical", 0),
        high_count=severity_counts.get("high", 0),
        medium_count=severity_counts.get("medium", 0),
        low_count=severity_counts.get("low", 0),
        info_count=severity_counts.get("info", 0),
        unreported_count=unreported_count,
        total_scans=total_scans,
        scans_24h=scans_24h,
        running_scans=running_scans,
        alerts_sent_24h=alerts_sent_24h,
        failed_alerts=failed_alerts,
        scope_changes_24h=scope_changes_24h,
        last_scan=last_scan,
        last_vulnerability=last_vulnerability,
        last_scope_check=last_scope_check,
    )


@router.get("/programs/{program_id}", response_model=ProgramStats)
async def get_program_stats(
    program_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get statistics for a specific program."""
    from fastapi import HTTPException
    
    # Get program
    program = await db.get(Program, program_id)
    if not program:
        raise HTTPException(status_code=404, detail="Program not found")
    
    # Assets
    total_assets_result = await db.execute(
        select(func.count(Asset.id)).where(Asset.program_id == program_id)
    )
    total_assets = total_assets_result.scalar() or 0
    
    alive_assets_result = await db.execute(
        select(func.count(Asset.id)).where(
            Asset.program_id == program_id,
            Asset.is_alive == True,
        )
    )
    alive_assets = alive_assets_result.scalar() or 0
    
    in_scope_assets_result = await db.execute(
        select(func.count(Asset.id)).where(
            Asset.program_id == program_id,
            Asset.in_scope == True,
            Asset.is_alive == True,
        )
    )
    in_scope_assets = in_scope_assets_result.scalar() or 0
    
    # Vulnerabilities by severity
    severity_counts = {}
    for severity in [SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM, SeverityLevel.LOW, SeverityLevel.INFO]:
        count_result = await db.execute(
            select(func.count(Vulnerability.id)).where(
                Vulnerability.program_id == program_id,
                Vulnerability.severity == severity,
            )
        )
        severity_counts[severity.value] = count_result.scalar() or 0
    
    # Scans
    total_scans_result = await db.execute(
        select(func.count(Scan.id)).where(Scan.program_id == program_id)
    )
    total_scans = total_scans_result.scalar() or 0
    
    last_scan_result = await db.execute(
        select(Scan.created_at)
        .where(Scan.program_id == program_id)
        .order_by(Scan.created_at.desc())
        .limit(1)
    )
    last_scan = last_scan_result.scalar_one_or_none()
    
    # Scope
    latest_scope_result = await db.execute(
        select(ScopeHistory)
        .where(ScopeHistory.program_id == program_id)
        .order_by(ScopeHistory.checked_at.desc())
        .limit(1)
    )
    latest_scope = latest_scope_result.scalar_one_or_none()
    
    in_scope_items = len(latest_scope.in_scope) if latest_scope and latest_scope.in_scope else 0
    out_scope_items = len(latest_scope.out_of_scope) if latest_scope and latest_scope.out_of_scope else 0
    last_scope_check = latest_scope.checked_at if latest_scope else None
    
    return ProgramStats(
        program_id=program_id,
        program_name=program.name,
        platform=program.platform,
        total_assets=total_assets,
        alive_assets=alive_assets,
        in_scope_assets=in_scope_assets,
        critical_count=severity_counts.get("critical", 0),
        high_count=severity_counts.get("high", 0),
        medium_count=severity_counts.get("medium", 0),
        low_count=severity_counts.get("low", 0),
        info_count=severity_counts.get("info", 0),
        total_scans=total_scans,
        last_scan=last_scan,
        in_scope_items=in_scope_items,
        out_scope_items=out_scope_items,
        last_scope_check=last_scope_check,
    )
