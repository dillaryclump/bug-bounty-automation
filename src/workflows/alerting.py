"""
Alerting Workflows
Prefect workflows for sending alerts and reports.
"""

from datetime import datetime, timedelta
from typing import List, Optional

from prefect import flow, task
from prefect.tasks import task_input_hash

from src.alerting.manager import AlertManager
from src.config import settings
from src.db.models import AlertType, SeverityLevel, Vulnerability
from src.db.session import db_manager
from src.utils.logging import get_logger

logger = get_logger(__name__)


@task(
    name="send_vulnerability_alert",
    retries=2,
    retry_delay_seconds=30,
    cache_key_fn=task_input_hash,
    cache_expiration=timedelta(hours=1),
)
async def send_vulnerability_alert_task(
    vulnerability_id: int,
    alert_type: AlertType = AlertType.NEW_VULNERABILITY,
) -> bool:
    """
    Send alert for a single vulnerability.
    
    Args:
        vulnerability_id: Vulnerability ID
        alert_type: Type of alert
        
    Returns:
        True if sent successfully
    """
    async with db_manager.get_session() as session:
        # Load vulnerability with relationships
        vuln = await session.get(
            Vulnerability,
            vulnerability_id,
            options=[
                # Eagerly load asset relationship
                # This avoids lazy loading issues
            ]
        )
        
        if not vuln:
            logger.error(f"Vulnerability {vulnerability_id} not found")
            return False

        async with AlertManager(session) as manager:
            success = await manager.alert_vulnerability(vuln, alert_type)
            
            if success:
                logger.info(f"✅ Alert sent for vulnerability {vulnerability_id}")
            else:
                logger.error(f"❌ Failed to send alert for vulnerability {vulnerability_id}")
            
            return success


@task(
    name="send_batch_vulnerability_alerts",
    retries=2,
    retry_delay_seconds=30,
)
async def send_batch_vulnerability_alerts_task(
    vulnerability_ids: List[int],
    title: str = "New Vulnerabilities Detected",
) -> bool:
    """
    Send batched vulnerability alerts.
    
    Args:
        vulnerability_ids: List of vulnerability IDs
        title: Alert title
        
    Returns:
        True if sent successfully
    """
    async with db_manager.get_session() as session:
        # Load vulnerabilities
        vulns = []
        for vuln_id in vulnerability_ids:
            vuln = await session.get(Vulnerability, vuln_id)
            if vuln:
                vulns.append(vuln)

        if not vulns:
            logger.warning("No vulnerabilities to alert on")
            return True

        async with AlertManager(session) as manager:
            success = await manager.alert_batch_vulnerabilities(vulns, title)
            
            if success:
                logger.info(f"✅ Batch alert sent for {len(vulns)} vulnerabilities")
            else:
                logger.error(f"❌ Failed to send batch alert")
            
            return success


@task(
    name="send_daily_summary",
    retries=2,
    retry_delay_seconds=60,
)
async def send_daily_summary_task(program_id: Optional[int] = None) -> bool:
    """
    Send daily summary report.
    
    Args:
        program_id: Optional program to filter by
        
    Returns:
        True if sent successfully
    """
    async with db_manager.get_session() as session:
        async with AlertManager(session) as manager:
            success = await manager.send_daily_summary(program_id)
            
            if success:
                logger.info("✅ Daily summary sent")
            else:
                logger.error("❌ Failed to send daily summary")
            
            return success


@task(
    name="retry_failed_alerts",
    retries=1,
)
async def retry_failed_alerts_task(max_retries: int = 3) -> int:
    """
    Retry failed alerts.
    
    Args:
        max_retries: Maximum retry attempts
        
    Returns:
        Number of alerts successfully retried
    """
    async with db_manager.get_session() as session:
        async with AlertManager(session) as manager:
            count = await manager.retry_failed_alerts(max_retries)
            logger.info(f"✅ Retried {count} failed alerts")
            return count


@task(
    name="test_alert_channels",
)
async def test_alert_channels_task() -> dict:
    """
    Test all configured alert channels.
    
    Returns:
        Dictionary of channel -> success status
    """
    async with db_manager.get_session() as session:
        async with AlertManager(session) as manager:
            results = await manager.test_alerts()
            
            for channel, success in results.items():
                if success:
                    logger.info(f"✅ {channel.title()} test successful")
                else:
                    logger.error(f"❌ {channel.title()} test failed")
            
            return results


@flow(
    name="alert_new_vulnerability",
    description="Send alert for a new vulnerability",
)
async def alert_new_vulnerability_flow(
    vulnerability_id: int,
    alert_type: AlertType = AlertType.NEW_VULNERABILITY,
) -> bool:
    """
    Flow to alert on a new vulnerability.
    
    Args:
        vulnerability_id: Vulnerability ID
        alert_type: Type of alert
        
    Returns:
        True if successful
    """
    logger.info(f"🔔 Sending alert for vulnerability {vulnerability_id}")
    
    success = await send_vulnerability_alert_task(vulnerability_id, alert_type)
    
    return success


@flow(
    name="alert_critical_findings",
    description="Send alerts for critical vulnerability findings",
)
async def alert_critical_findings_flow(vulnerability_ids: List[int]) -> bool:
    """
    Flow to alert on critical findings immediately.
    
    Args:
        vulnerability_ids: List of critical vulnerability IDs
        
    Returns:
        True if successful
    """
    if not vulnerability_ids:
        logger.info("No critical findings to alert on")
        return True

    logger.info(f"🚨 Sending critical alerts for {len(vulnerability_ids)} findings")
    
    # Send individual alerts for critical findings (not batched)
    results = []
    for vuln_id in vulnerability_ids:
        success = await send_vulnerability_alert_task(
            vuln_id,
            AlertType.CRITICAL_FINDING,
        )
        results.append(success)
    
    return all(results)


@flow(
    name="alert_batch_findings",
    description="Send batched alerts for multiple findings",
)
async def alert_batch_findings_flow(
    vulnerability_ids: List[int],
    title: str = "New Vulnerabilities Detected",
) -> bool:
    """
    Flow to send batched vulnerability alerts.
    
    Args:
        vulnerability_ids: List of vulnerability IDs
        title: Alert title
        
    Returns:
        True if successful
    """
    if not vulnerability_ids:
        logger.info("No findings to alert on")
        return True

    logger.info(f"📦 Sending batch alert for {len(vulnerability_ids)} findings")
    
    success = await send_batch_vulnerability_alerts_task(vulnerability_ids, title)
    
    return success


@flow(
    name="daily_summary_report",
    description="Send daily summary report of findings",
)
async def daily_summary_report_flow(program_id: Optional[int] = None) -> bool:
    """
    Flow to send daily summary report.
    
    Args:
        program_id: Optional program to filter by
        
    Returns:
        True if successful
    """
    logger.info("📊 Generating and sending daily summary report")
    
    success = await send_daily_summary_task(program_id)
    
    return success


@flow(
    name="weekly_digest_report",
    description="Send weekly digest report",
)
async def weekly_digest_report_flow(program_id: Optional[int] = None) -> bool:
    """
    Flow to send weekly digest report.
    
    Args:
        program_id: Optional program to filter by
        
    Returns:
        True if successful
    """
    logger.info("📈 Generating and sending weekly digest report")
    
    # Calculate stats for last 7 days
    async with db_manager.get_session() as session:
        from sqlalchemy import select, and_
        from src.db.models import Vulnerability, Asset
        
        since = datetime.utcnow() - timedelta(days=7)
        
        filters = [Vulnerability.first_seen >= since]
        if program_id:
            filters.append(Vulnerability.asset.has(Asset.program_id == program_id))
        
        result = await session.execute(
            select(Vulnerability).where(and_(*filters))
        )
        vulns = list(result.scalars().all())
        
        stats = {
            "Total Vulnerabilities": len(vulns),
            "Critical": sum(1 for v in vulns if v.severity == SeverityLevel.CRITICAL),
            "High": sum(1 for v in vulns if v.severity == SeverityLevel.HIGH),
            "Medium": sum(1 for v in vulns if v.severity == SeverityLevel.MEDIUM),
            "Reported": sum(1 for v in vulns if v.reported),
            "Pending Report": sum(1 for v in vulns if not v.reported),
        }
        
        title = "Weekly Security Digest"
        description = f"Summary of findings from the last 7 days"
        
        async with AlertManager(session) as manager:
            success = False
            if settings.discord_webhook_url:
                success = await manager.discord.send_summary(
                    title, description, stats, AlertType.WEEKLY_DIGEST
                )
            if settings.slack_webhook_url:
                slack_success = await manager.slack.send_summary(
                    title, description, stats, AlertType.WEEKLY_DIGEST
                )
                success = success or slack_success
            
            # Create alert record
            await manager.repository.create(
                alert_type=AlertType.WEEKLY_DIGEST,
                title=title,
                message=description,
                channel="both" if settings.discord_webhook_url and settings.slack_webhook_url else "discord",
                destination=settings.discord_webhook_url or settings.slack_webhook_url or "",
                program_id=program_id,
                payload=stats,
            )
            await session.commit()
            
            return success


@flow(
    name="test_alerts",
    description="Test all configured alert channels",
)
async def test_alerts_flow() -> dict:
    """
    Flow to test alert channels.
    
    Returns:
        Dictionary of test results
    """
    logger.info("🧪 Testing alert channels")
    
    results = await test_alert_channels_task()
    
    return results


@flow(
    name="retry_failed_alerts",
    description="Retry failed alert deliveries",
)
async def retry_failed_alerts_flow(max_retries: int = 3) -> int:
    """
    Flow to retry failed alerts.
    
    Args:
        max_retries: Maximum retry attempts
        
    Returns:
        Number of alerts successfully retried
    """
    logger.info("🔄 Retrying failed alerts")
    
    count = await retry_failed_alerts_task(max_retries)
    
    logger.info(f"✅ Retried {count} alerts")
    return count
