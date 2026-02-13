"""
Export routes - Export data in various formats
"""

import csv
import io
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
import json

from src.api.dependencies.database import get_db
from src.api.dependencies.auth import require_auth
from src.db.repositories.program_repository import ProgramRepository
from src.db.repositories.asset_repository import AssetRepository
from src.db.repositories.vulnerability_repository import VulnerabilityRepository
from src.db.repositories.scan_repository import ScanRepository
from src.db.repositories.alert_repository import AlertRepository
from src.db.models import User


router = APIRouter(prefix="/export", tags=["Export"])


def jsonresponse(data: list[dict], filename: str) -> Response:
    """Create a JSON file download response."""
    json_str = json.dumps(data, indent=2, default=str)
    
    return Response(
        content=json_str,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


def csv_response(data: list[dict], filename: str) -> StreamingResponse:
    """Create a CSV file download response."""
    if not data:
        return StreamingResponse(
            iter([""]),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=data[0].keys())
    writer.writeheader()
    writer.writerows(data)
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@router.get("/programs")
async def export_programs(
    format: str = Query("json", pattern="^(json|csv)$"),
    platform: Optional[str] = None,
    is_active: Optional[bool] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Export programs to JSON or CSV.
    
    Query parameters:
    - format: json or csv
    - platform: Filter by platform
    - is_active: Filter by active status
    """
    repo = ProgramRepository(db)
    programs = await repo.list(platform=platform, is_active=is_active, limit=10000)
    
    # Convert to dict
    data = [
        {
            "id": p.id,
            "platform": p.platform,
            "handle": p.program_handle,
            "name": p.program_name,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
            "updated_at": p.updated_at.isoformat() if p.updated_at else None
        }
        for p in programs
    ]
    
    filename = f"programs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    if format == "csv":
        return csv_response(data, filename)
    else:
        return jsonresponse(data, filename)


@router.get("/assets")
async def export_assets(
    format: str = Query("json", pattern="^(json|csv)$"),
    program_id: Optional[int] = None,
    asset_type: Optional[str] = None,
    is_alive: Optional[bool] = None,
    in_scope: Optional[bool] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Export assets to JSON or CSV.
    
    Query parameters:
    - format: json or csv
    - program_id: Filter by program
    - asset_type: Filter by type
    - is_alive: Filter by alive status
    - in_scope: Filter by scope status
    """
    repo = AssetRepository(db)
    assets = await repo.list(
        program_id=program_id,
        asset_type=asset_type,
        is_alive=is_alive,
        in_scope=in_scope,
        limit=10000
    )
    
    # Convert to dict
    data = [
        {
            "id": a.id,
            "program_id": a.program_id,
            "asset_type": a.asset_type,
            "value": a.value,
            "is_alive": a.is_alive,
            "in_scope": a.in_scope,
            "http_status": a.http_status_code,
            "title": a.http_title,
            "technologies": ",".join(a.technologies) if a.technologies else "",
            "discovered_at": a.discovered_at.isoformat() if a.discovered_at else None
        }
        for a in assets
    ]
    
    filename = f"assets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    if format == "csv":
        return csv_response(data, filename)
    else:
        return jsonresponse(data, filename)


@router.get("/vulnerabilities")
async def export_vulnerabilities(
    format: str = Query("json", pattern="^(json|csv)$"),
    program_id: Optional[int] = None,
    severity: Optional[str] = None,
    is_reported: Optional[bool] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Export vulnerabilities to JSON or CSV.
    
    Query parameters:
    - format: json or csv
    - program_id: Filter by program
    - severity: Filter by severity
    - is_reported: Filter by reported status
    """
    repo = VulnerabilityRepository(db)
    vulns = await repo.list(
        program_id=program_id,
        severity=severity,
        is_reported=is_reported,
        limit=10000
    )
    
    # Convert to dict
    data = [
        {
            "id": v.id,
            "program_id": v.program_id,
            "asset_id": v.asset_id,
            "template_id": v.template_id,
            "template_name": v.template_name,
            "severity": v.severity.value if v.severity else "",
            "matched_at": v.matched_at,
            "matcher_name": v.matcher_name,
            "is_reported": v.is_reported,
            "reported_at": v.reported_at.isoformat() if v.reported_at else None,
            "discovered_at": v.discovered_at.isoformat() if v.discovered_at else None
        }
        for v in vulns
    ]
    
    filename = f"vulnerabilities_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    if format == "csv":
        return csv_response(data, filename)
    else:
        return jsonresponse(data, filename)


@router.get("/scans")
async def export_scans(
    format: str = Query("json", pattern="^(json|csv)$"),
    program_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Export scans to JSON or CSV.
    
    Query parameters:
    - format: json or csv
    - program_id: Filter by program
    - status: Filter by status
    """
    repo = ScanRepository(db)
    scans = await repo.list(
        program_id=program_id,
        status=status,
        limit=10000
    )
    
    # Convert to dict
    data = [
        {
            "id": s.id,
            "program_id": s.program_id,
            "scan_type": s.scan_type.value if s.scan_type else "",
            "status": s.status.value if s.status else "",
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "error_message": s.error_message,
            "result_summary": s.result_summary
        }
        for s in scans
    ]
    
    filename = f"scans_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    if format == "csv":
        return csv_response(data, filename)
    else:
        return jsonresponse(data, filename)


@router.get("/alerts")
async def export_alerts(
    format: str = Query("json", pattern="^(json|csv)$"),
    channel: Optional[str] = None,
    sent_successfully: Optional[bool] = None,
    current_user: User = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    """
    Export alerts to JSON or CSV.
    
    Query parameters:
    - format: json or csv
    - channel: Filter by channel
    - sent_successfully: Filter by success status
    """
    repo = AlertRepository(db)
    alerts = await repo.list(
        channel=channel,
        sent_successfully=sent_successfully,
        limit=10000
    )
    
    # Convert to dict
    data = [
        {
            "id": a.id,
            "alert_type": a.alert_type.value if a.alert_type else "",
            "channel": a.channel,
            "title": a.title,
            "message": a.message,
            "sent_successfully": a.sent_successfully,
            "error_message": a.error_message,
            "sent_at": a.sent_at.isoformat() if a.sent_at else None
        }
        for a in alerts
    ]
    
    filename = f"alerts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
    
    if format == "csv":
        return csv_response(data, filename)
    else:
        return jsonresponse(data, filename)
