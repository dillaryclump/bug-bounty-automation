"""
Alert Manager
Coordinates alert delivery across multiple channels and manages alert history.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.alerting.discord import DiscordAlertClient
from src.alerting.slack import SlackAlertClient
from src.config import settings
from src.db.models import (
    Alert,
    AlertType,
    Asset,
    Program,
    SeverityLevel,
    Vulnerability,
    ScopeHistory,
)
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AlertRepository:
    """Repository for Alert database operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        alert_type: AlertType,
        title: str,
        message: str,
        channel: str,
        destination: str,
        program_id: Optional[int] = None,
        vulnerability_id: Optional[int] = None,
        asset_id: Optional[int] = None,
        severity: Optional[SeverityLevel] = None,
        payload: Optional[dict] = None,
    ) -> Alert:
        """Create new alert record."""
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            program_id=program_id,
            vulnerability_id=vulnerability_id,
            asset_id=asset_id,
            title=title,
            message=message,
            payload=payload,
            channel=channel,
            destination=destination,
        )
        self.session.add(alert)
        await self.session.flush()
        return alert

    async def mark_sent(
        self,
        alert_id: int,
        success: bool,
        error_message: Optional[str] = None,
    ) -> None:
        """Mark alert as sent."""
        alert = await self.session.get(Alert, alert_id)
        if alert:
            alert.sent = True
            alert.success = success
            alert.sent_at = datetime.utcnow()
            alert.error_message = error_message
            if not success:
                alert.retry_count += 1

    async def get_recent_alerts(
        self,
        hours: int = 24,
        alert_type: Optional[AlertType] = None,
        program_id: Optional[int] = None,
    ) -> List[Alert]:
        """Get recent alerts."""
        since = datetime.utcnow() - timedelta(hours=hours)
        
        filters = [Alert.created_at >= since]
        if alert_type:
            filters.append(Alert.alert_type == alert_type)
        if program_id:
            filters.append(Alert.program_id == program_id)

        result = await self.session.execute(
            select(Alert)
            .where(and_(*filters))
            .order_by(Alert.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_failed_alerts(self, max_retries: int = 3) -> List[Alert]:
        """Get alerts that failed to send and eligible for retry."""
        result = await self.session.execute(
            select(Alert).where(
                and_(
                    Alert.sent == True,
                    Alert.success == False,
                    Alert.retry_count < max_retries,
                )
            )
        )
        return list(result.scalars().all())

    async def get_stats(
        self,
        days: int = 7,
        program_id: Optional[int] = None,
    ) -> Dict:
        """Get alert statistics."""
        since = datetime.utcnow() - timedelta(days=days)
        
        filters = [Alert.created_at >= since]
        if program_id:
            filters.append(Alert.program_id == program_id)

        result = await self.session.execute(
            select(Alert).where(and_(*filters))
        )
        alerts = list(result.scalars().all())

        stats = {
            "total_alerts": len(alerts),
            "successful": sum(1 for a in alerts if a.success),
            "failed": sum(1 for a in alerts if a.sent and not a.success),
            "pending": sum(1 for a in alerts if not a.sent),
        }

        # By type
        by_type = {}
        for alert in alerts:
            by_type[alert.alert_type.value] = by_type.get(alert.alert_type.value, 0) + 1
        stats["by_type"] = by_type

        # By channel
        by_channel = {}
        for alert in alerts:
            by_channel[alert.channel] = by_channel.get(alert.channel, 0) + 1
        stats["by_channel"] = by_channel

        return stats


class AlertManager:
    """
    Centralized alert management.
    Handles routing, delivery, batching, and history tracking.
    """

    def __init__(
        self,
        session: AsyncSession,
        discord_client: Optional[DiscordAlertClient] = None,
        slack_client: Optional[SlackAlertClient] = None,
    ):
        """
        Initialize alert manager.
        
        Args:
            session: Database session
            discord_client: Discord client (created if None)
            slack_client: Slack client (created if None)
        """
        self.session = session
        self.repository = AlertRepository(session)
        
        # Initialize clients
        self.discord = discord_client or DiscordAlertClient()
        self.slack = slack_client or SlackAlertClient()
        
        # Alert batching
        self._batch_window = settings.alert_batch_window
        self._batched_alerts: Dict[str, List[Vulnerability]] = {}

    async def close(self):
        """Close all clients."""
        await self.discord.close()
        await self.slack.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _should_alert(self, severity: SeverityLevel) -> bool:
        """Check if severity meets alert threshold."""
        severity_order = {
            SeverityLevel.INFO: 0,
            SeverityLevel.LOW: 1,
            SeverityLevel.MEDIUM: 2,
            SeverityLevel.HIGH: 3,
            SeverityLevel.CRITICAL: 4,
        }
        
        min_severity = getattr(
            SeverityLevel,
            settings.alert_min_severity.upper(),
            SeverityLevel.HIGH
        )
        
        return severity_order.get(severity, 0) >= severity_order.get(min_severity, 3)

    def _get_channel_for_severity(self, severity: SeverityLevel) -> str:
        """Determine which channel to use based on severity."""
        if severity == SeverityLevel.CRITICAL:
            # Critical alerts go to configured critical channel
            channel = settings.alert_critical_channel
            if channel == "both":
                return "both"
            elif channel == "slack":
                return "slack"
            else:
                return "discord"  # Default
        
        # Non-critical: use whichever is configured
        if settings.discord_webhook_url:
            return "discord"
        elif settings.slack_webhook_url:
            return "slack"
        else:
            logger.warning("No alert channels configured")
            return "none"

    async def _send_to_channel(
        self,
        channel: str,
        vulnerability: Vulnerability,
        alert_type: AlertType = AlertType.NEW_VULNERABILITY,
    ) -> bool:
        """Send alert to specific channel."""
        success = False
        
        if channel == "discord" and settings.discord_webhook_url:
            success = await self.discord.send_vulnerability_alert(
                vulnerability, alert_type
            )
        elif channel == "slack" and settings.slack_webhook_url:
            success = await self.slack.send_vulnerability_alert(
                vulnerability, alert_type
            )
        elif channel == "both":
            discord_success = await self._send_to_channel("discord", vulnerability, alert_type)
            slack_success = await self._send_to_channel("slack", vulnerability, alert_type)
            success = discord_success or slack_success
        
        return success

    async def alert_vulnerability(
        self,
        vulnerability: Vulnerability,
        alert_type: AlertType = AlertType.NEW_VULNERABILITY,
    ) -> bool:
        """
        Send alert for a single vulnerability.
        
        Args:
            vulnerability: Vulnerability to alert on
            alert_type: Type of alert
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Check severity threshold
        if not self._should_alert(vulnerability.severity):
            logger.debug(
                f"Skipping alert for {vulnerability.severity.value} vulnerability "
                f"(below threshold: {settings.alert_min_severity})"
            )
            return True  # Not an error, just filtered

        # Determine channel
        channel = self._get_channel_for_severity(vulnerability.severity)
        if channel == "none":
            return False

        # Create alert record
        alert = await self.repository.create(
            alert_type=alert_type,
            severity=vulnerability.severity,
            title=vulnerability.name,
            message=f"New vulnerability found: {vulnerability.matched_at}",
            channel=channel,
            destination=settings.discord_webhook_url or settings.slack_webhook_url or "",
            program_id=vulnerability.asset.program_id if vulnerability.asset else None,
            vulnerability_id=vulnerability.id,
            asset_id=vulnerability.asset_id,
            payload={
                "template_id": vulnerability.template_id,
                "matched_at": vulnerability.matched_at,
            },
        )

        # Send to channel(s)
        success = await self._send_to_channel(channel, vulnerability, alert_type)

        # Update alert record
        await self.repository.mark_sent(
            alert.id,
            success=success,
            error_message=None if success else "Failed to send alert",
        )
        await self.session.commit()

        return success

    async def alert_batch_vulnerabilities(
        self,
        vulnerabilities: List[Vulnerability],
        title: str = "New Vulnerabilities Detected",
    ) -> bool:
        """
        Send batched vulnerability alerts.
        
        Args:
            vulnerabilities: List of vulnerabilities
            title: Alert title
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not vulnerabilities:
            return True

        # Filter by severity threshold
        filtered = [v for v in vulnerabilities if self._should_alert(v.severity)]
        if not filtered:
            logger.debug("No vulnerabilities meet alert threshold")
            return True

        # Find highest severity to determine channel
        max_severity = max(v.severity for v in filtered)
        channel = self._get_channel_for_severity(max_severity)
        if channel == "none":
            return False

        # Create alert records
        for vuln in filtered:
            await self.repository.create(
                alert_type=AlertType.NEW_VULNERABILITY,
                severity=vuln.severity,
                title=title,
                message=f"Batch alert: {len(filtered)} vulnerabilities",
                channel=channel,
                destination=settings.discord_webhook_url or settings.slack_webhook_url or "",
                program_id=vuln.asset.program_id if vuln.asset else None,
                vulnerability_id=vuln.id,
                asset_id=vuln.asset_id,
            )

        # Send batch to channel(s)
        success = False
        if channel == "discord" and settings.discord_webhook_url:
            success = await self.discord.send_batch_vulnerabilities(filtered, title)
        elif channel == "slack" and settings.slack_webhook_url:
            success = await self.slack.send_batch_vulnerabilities(filtered, title)
        elif channel == "both":
            discord_success = await self.discord.send_batch_vulnerabilities(filtered, title)
            slack_success = await self.slack.send_batch_vulnerabilities(filtered, title)
            success = discord_success or slack_success

        await self.session.commit()
        return success

    async def send_daily_summary(self, program_id: Optional[int] = None) -> bool:
        """
        Send daily summary report.
        
        Args:
            program_id: Optional program to filter by
            
        Returns:
            True if sent successfully, False otherwise
        """
        # Calculate stats for last 24 hours
        since = datetime.utcnow() - timedelta(hours=24)

        # Query vulnerabilities
        filters = [Vulnerability.first_seen >= since]
        if program_id:
            filters.append(Vulnerability.asset.has(Asset.program_id == program_id))

        result = await self.session.execute(
            select(Vulnerability).where(and_(*filters))
        )
        vulns = list(result.scalars().all())

        # Build stats
        stats = {
            "Total Vulnerabilities": len(vulns),
            "Critical": sum(1 for v in vulns if v.severity == SeverityLevel.CRITICAL),
            "High": sum(1 for v in vulns if v.severity == SeverityLevel.HIGH),
            "Medium": sum(1 for v in vulns if v.severity == SeverityLevel.MEDIUM),
            "Low": sum(1 for v in vulns if v.severity == SeverityLevel.LOW),
            "Info": sum(1 for v in vulns if v.severity == SeverityLevel.INFO),
        }

        title = "Daily Security Summary"
        description = f"Vulnerability findings from the last 24 hours"

        # Send to configured channels
        success = False
        if settings.discord_webhook_url:
            success = await self.discord.send_summary(
                title, description, stats, AlertType.DAILY_SUMMARY
            )
        if settings.slack_webhook_url:
            slack_success = await self.slack.send_summary(
                title, description, stats, AlertType.DAILY_SUMMARY
            )
            success = success or slack_success

        # Create alert record
        await self.repository.create(
            alert_type=AlertType.DAILY_SUMMARY,
            title=title,
            message=description,
            channel="both" if settings.discord_webhook_url and settings.slack_webhook_url else "discord",
            destination=settings.discord_webhook_url or settings.slack_webhook_url or "",
            program_id=program_id,
            payload=stats,
        )
        await self.session.commit()

        return success

    async def test_alerts(self) -> Dict[str, bool]:
        """
        Test all configured alert channels.
        
        Returns:
            Dictionary of channel -> success status
        """
        results = {}

        if settings.discord_webhook_url:
            logger.info("Testing Discord webhook...")
            results["discord"] = await self.discord.test_connection()
        else:
            logger.warning("Discord webhook not configured")
            results["discord"] = False

        if settings.slack_webhook_url:
            logger.info("Testing Slack webhook...")
            results["slack"] = await self.slack.test_connection()
        else:
            logger.warning("Slack webhook not configured")
            results["slack"] = False

        return results

    async def retry_failed_alerts(self, max_retries: int = 3) -> int:
        """
        Retry failed alerts.
        
        Args:
            max_retries: Maximum retry attempts
            
        Returns:
            Number of alerts successfully retried
        """
        failed = await self.repository.get_failed_alerts(max_retries)
        success_count = 0

        for alert in failed:
            logger.info(f"Retrying alert {alert.id} (attempt {alert.retry_count + 1})")
            
            # Get the vulnerability if it exists
            if alert.vulnerability_id:
                vuln = await self.session.get(Vulnerability, alert.vulnerability_id)
                if vuln:
                    success = await self._send_to_channel(
                        alert.channel, vuln, alert.alert_type
                    )
                    await self.repository.mark_sent(
                        alert.id,
                        success=success,
                        error_message=None if success else "Retry failed",
                    )
                    if success:
                        success_count += 1

        await self.session.commit()
        return success_count
    
    async def alert_scope_change(
        self,
        program: Program,
        scope_history: ScopeHistory,
        changes_summary: Dict,
    ) -> bool:
        """
        Send alert for program scope changes.
        
        Args:
            program: Program with scope changes
            scope_history: Scope history record
            changes_summary: Dict with change details
            
        Returns:
            True if sent successfully, False otherwise
        """
        if not changes_summary.get("has_changes"):
            logger.debug("No scope changes to alert on")
            return True
        
        # Skip first check alerts (too noisy)
        if changes_summary.get("is_first_check"):
            logger.debug("Skipping alert for first scope check (baseline)")
            return True
        
        # Determine channel (always alert on scope changes)
        channel = settings.alert_default_channel or "discord"
        
        # Build title and message
        title = f"🎯 Scope Change: {program.name}"
        summary = changes_summary.get("summary", "Scope updated")
        message = f"Program scope has been updated: {summary}"
        
        # Create alert record
        alert = await self.repository.create(
            alert_type=AlertType.SCOPE_CHANGE,
            severity=SeverityLevel.INFO,  # Scope changes are informational
            title=title,
            message=message,
            channel=channel,
            destination=settings.discord_webhook_url or settings.slack_webhook_url or "",
            program_id=program.id,
            payload={
                "scope_history_id": scope_history.id,
                "changes": changes_summary.get("changes", []),
                "additions": changes_summary.get("additions", 0),
                "removals": changes_summary.get("removals", 0),
                "modifications": changes_summary.get("modifications", 0),
            },
        )
        
        # Format changes for webhook
        changes_list = changes_summary.get("changes", [])[:10]  # Limit to 10
        changes_text = []
        for change in changes_list:
            symbol = {
                "added": "+",
                "removed": "-",
                "modified": "~",
            }.get(change.get("type"), "?")
            item = change.get("item", "")
            category = change.get("category", "")
            changes_text.append(f"{symbol} [{category}] {item}")
        
        changes_description = "\n".join(changes_text)
        if len(changes_summary.get("changes", [])) > 10:
            remaining = len(changes_summary.get("changes", [])) - 10
            changes_description += f"\n... and {remaining} more changes"
        
        # Send to Discord if configured
        success = False
        if channel in ["discord", "both"] and settings.discord_webhook_url:
            try:
                embed = {
                    "title": title,
                    "description": message,
                    "color": 0x00FF00,  # Green for scope changes
                    "fields": [
                        {
                            "name": "Program",
                            "value": f"[{program.name}]({program.url})",
                            "inline": True,
                        },
                        {
                            "name": "Platform",
                            "value": program.platform.upper(),
                            "inline": True,
                        },
                        {
                            "name": "Changes",
                            "value": (
                                f"**Added:** {changes_summary.get('additions', 0)}\n"
                                f"**Removed:** {changes_summary.get('removals', 0)}\n"
                                f"**Modified:** {changes_summary.get('modifications', 0)}"
                            ),
                            "inline": False,
                        },
                        {
                            "name": "Details",
                            "value": f"```diff\n{changes_description}\n```",
                            "inline": False,
                        },
                    ],
                    "timestamp": datetime.utcnow().isoformat(),
                    "footer": {
                        "text": f"Scope checked at {scope_history.checked_at.strftime('%Y-%m-%d %H:%M UTC')}",
                    },
                }
                
                await self.discord.send_custom_message(
                    title=title,
                    message=message,
                    embeds=[embed],
                )
                success = True
                logger.info(f"Sent scope change alert to Discord for program {program.id}")
            except Exception as e:
                logger.error(f"Failed to send Discord scope alert: {e}")
        
        # Send to Slack if configured
        if channel in ["slack", "both"] and settings.slack_webhook_url:
            try:
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": title,
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message,
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Program:*\n<{program.url}|{program.name}>",
                            },
                            {
                                "type": "mrkdwn",
                                "text": f"*Platform:*\n{program.platform.upper()}",
                            },
                            {
                                "type": "mrkdwn",
                                "text": (
                                    f"*Added:* {changes_summary.get('additions', 0)}\n"
                                    f"*Removed:* {changes_summary.get('removals', 0)}\n"
                                    f"*Modified:* {changes_summary.get('modifications', 0)}"
                                ),
                            },
                        ],
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Changes:*\n```{changes_description}```",
                        },
                    },
                ]
                
                await self.slack.send_custom_message(
                    text=message,
                    blocks=blocks,
                )
                success = True
                logger.info(f"Sent scope change alert to Slack for program {program.id}")
            except Exception as e:
                logger.error(f"Failed to send Slack scope alert: {e}")
        
        # Update alert record
        await self.repository.mark_sent(
            alert.id,
            success=success,
            error_message=None if success else "Failed to send alert",
        )
        await self.session.commit()
        
        return success
