"""
Alert API Routes
Endpoints for managing alerts.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_db
from src.api.schemas.alerts import (
    AlertResponse,
    AlertListResponse,
    AlertCreate,
    AlertStatsResponse,
)
from src.db.models import Alert, AlertType
from src.utils.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    program_id: Optional[int] = Query(None, description="Filter by program ID"),
    alert_type: Optional[str] = Query(None, description="Filter by alert type"),
    sent: Optional[bool] = Query(None, description="Filter by sent status"),
    failed_only: bool = Query(False, description="Only show failed alerts"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """List all alerts with optional filtering."""
    # Build query
    query = select(Alert)
    
    if program_id:
        query = query.where(Alert.program_id == program_id)
    if alert_type:
        query = query.where(Alert.alert_type == alert_type)
    if sent is not None:
        query = query.where(Alert.sent == sent)
    if failed_only:
        query = query.where(Alert.sent == True, Alert.success == False)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get alerts with pagination
    query = query.offset(skip).limit(limit).order_by(Alert.created_at.desc())
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return AlertListResponse(
        total=total,
        alerts=[AlertResponse.model_validate(alert) for alert in alerts],
    )


@router.get("/stats", response_model=AlertStatsResponse)
async def get_alert_stats(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    db: AsyncSession = Depends(get_db),
):
    """Get alert statistics."""
    from datetime import datetime, timedelta
    
    since = datetime.utcnow() - timedelta(days=days)
    
    # Total sent
    sent_result = await db.execute(
        select(func.count(Alert.id)).where(Alert.sent == True, Alert.created_at >= since)
    )
    total_sent = sent_result.scalar() or 0
    
    # Total failed
    failed_result = await db.execute(
        select(func.count(Alert.id)).where(
            Alert.sent == True,
            Alert.success == False,
            Alert.created_at >= since,
        )
    )
    total_failed = failed_result.scalar() or 0
    
    # By type
    by_type = {}
    for alert_type in AlertType:
        type_result = await db.execute(
            select(func.count(Alert.id)).where(
                Alert.alert_type == alert_type.value,
                Alert.created_at >= since,
            )
        )
        by_type[alert_type.value] = type_result.scalar() or 0
    
    # By channel
    by_channel = {}
    for channel in ["discord", "slack", "both"]:
        channel_result = await db.execute(
            select(func.count(Alert.id)).where(
                Alert.channel == channel,
                Alert.created_at >= since,
            )
        )
        by_channel[channel] = channel_result.scalar() or 0
    
    # Success rate
    success_rate = (total_sent - total_failed) / total_sent * 100 if total_sent > 0 else 0
    
    return AlertStatsResponse(
        total_sent=total_sent,
        total_failed=total_failed,
        by_type=by_type,
        by_channel=by_channel,
        success_rate=round(success_rate, 2),
    )


@router.post("/retry-failed", status_code=200)
async def retry_failed_alerts(
    max_retries: int = Query(3, ge=1, le=10),
    db: AsyncSession = Depends(get_db),
):
    """Retry failed alerts."""
    from src.alerting.manager import AlertManager
    
    async with AlertManager(db) as manager:
        retried_count = await manager.retry_failed_alerts(max_retries=max_retries)
    
    return {
        "success": True,
        "retried_count": retried_count,
        "message": f"Retried {retried_count} failed alerts",
    }


@router.post("/test", status_code=200)
async def test_webhooks(
    db: AsyncSession = Depends(get_db),
):
    """Test webhook configurations."""
    from src.alerting.manager import AlertManager
    
    async with AlertManager(db) as manager:
        results = await manager.test_webhooks()
    
    return {
        "success": True,
        "results": results,
        "message": "Webhook test completed",
    }
