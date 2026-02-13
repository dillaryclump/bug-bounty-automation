"""
Discord Alert Client
Sends rich embed notifications to Discord via webhooks.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import httpx

from src.config import settings
from src.db.models import Alert, AlertType, SeverityLevel, Vulnerability
from src.utils.logging import get_logger

logger = get_logger(__name__)


class DiscordAlertClient:
    """Client for sending alerts to Discord via webhooks."""

    # Discord color codes
    COLORS = {
        SeverityLevel.CRITICAL: 0xFF0000,  # Red
        SeverityLevel.HIGH: 0xFF8C00,      # Dark Orange
        SeverityLevel.MEDIUM: 0xFFD700,    # Gold
        SeverityLevel.LOW: 0x87CEEB,       # Sky Blue
        SeverityLevel.INFO: 0x808080,      # Gray
    }

    # Alert type emojis
    EMOJIS = {
        AlertType.NEW_VULNERABILITY: "🐛",
        AlertType.CRITICAL_FINDING: "🚨",
        AlertType.NEW_ASSET: "🆕",
        AlertType.SCOPE_CHANGE: "🎯",
        AlertType.DAILY_SUMMARY: "📊",
        AlertType.WEEKLY_DIGEST: "📈",
        AlertType.SCAN_COMPLETE: "✅",
        AlertType.SCAN_FAILED: "❌",
    }

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Discord client.
        
        Args:
            webhook_url: Discord webhook URL (defaults to settings)
        """
        self.webhook_url = webhook_url or settings.discord_webhook_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _get_severity_color(self, severity: Optional[SeverityLevel]) -> int:
        """Get Discord color for severity level."""
        return self.COLORS.get(severity, 0x808080)

    def _get_alert_emoji(self, alert_type: AlertType) -> str:
        """Get emoji for alert type."""
        return self.EMOJIS.get(alert_type, "📢")

    def _build_vulnerability_embed(
        self,
        vuln: Vulnerability,
        alert_type: AlertType = AlertType.NEW_VULNERABILITY,
    ) -> Dict:
        """
        Build Discord embed for vulnerability alert.
        
        Args:
            vuln: Vulnerability object
            alert_type: Type of alert
            
        Returns:
            Discord embed dictionary
        """
        emoji = self._get_alert_emoji(alert_type)
        color = self._get_severity_color(vuln.severity)

        embed = {
            "title": f"{emoji} {vuln.name}",
            "description": f"**Matched At:** {vuln.matched_at}",
            "color": color,
            "fields": [
                {
                    "name": "Severity",
                    "value": f"`{vuln.severity.value.upper()}`",
                    "inline": True,
                },
                {
                    "name": "Template",
                    "value": f"`{vuln.template_id}`",
                    "inline": True,
                },
                {
                    "name": "First Seen",
                    "value": f"<t:{int(vuln.first_seen.timestamp())}:R>",
                    "inline": True,
                },
            ],
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add asset info if available
        if vuln.asset:
            embed["fields"].append({
                "name": "Asset",
                "value": f"`{vuln.asset.value}`",
                "inline": False,
            })

        # Add tags if available
        if vuln.tags:
            tags_str = ", ".join([f"`{tag}`" for tag in vuln.tags[:5]])
            embed["fields"].append({
                "name": "Tags",
                "value": tags_str,
                "inline": False,
            })

        # Add curl command if available
        if vuln.curl_command:
            # Truncate if too long
            curl = vuln.curl_command
            if len(curl) > 500:
                curl = curl[:497] + "..."
            embed["fields"].append({
                "name": "Reproduction",
                "value": f"```bash\n{curl}\n```",
                "inline": False,
            })

        return embed

    def _build_summary_embed(
        self,
        title: str,
        description: str,
        stats: Dict,
        alert_type: AlertType = AlertType.DAILY_SUMMARY,
    ) -> Dict:
        """
        Build Discord embed for summary reports.
        
        Args:
            title: Summary title
            description: Summary description
            stats: Statistics dictionary
            alert_type: Type of alert
            
        Returns:
            Discord embed dictionary
        """
        emoji = self._get_alert_emoji(alert_type)
        
        embed = {
            "title": f"{emoji} {title}",
            "description": description,
            "color": 0x5865F2,  # Discord Blurple
            "fields": [],
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add stat fields
        for key, value in stats.items():
            embed["fields"].append({
                "name": key,
                "value": str(value),
                "inline": True,
            })

        return embed

    async def send_vulnerability_alert(
        self,
        vulnerability: Vulnerability,
        alert_type: AlertType = AlertType.NEW_VULNERABILITY,
    ) -> bool:
        """
        Send vulnerability alert to Discord.
        
        Args:
            vulnerability: Vulnerability to alert on
            alert_type: Type of alert
            
        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
            return False

        try:
            embed = self._build_vulnerability_embed(vulnerability, alert_type)
            
            payload = {
                "username": "AutoBug Security Alert",
                "avatar_url": "https://i.imgur.com/4M34hi2.png",  # Optional: Add your logo
                "embeds": [embed],
            }

            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            logger.info(f"Sent Discord alert for vulnerability {vulnerability.id}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord alert: {e}")
            return False

    async def send_batch_vulnerabilities(
        self,
        vulnerabilities: List[Vulnerability],
        title: str = "New Vulnerabilities Detected",
    ) -> bool:
        """
        Send batch of vulnerabilities as a single message.
        
        Args:
            vulnerabilities: List of vulnerabilities
            title: Message title
            
        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
            return False

        if not vulnerabilities:
            return True

        try:
            # Discord has a 10 embed limit, so send in batches
            batch_size = 10
            for i in range(0, len(vulnerabilities), batch_size):
                batch = vulnerabilities[i:i + batch_size]
                
                embeds = [
                    self._build_vulnerability_embed(vuln)
                    for vuln in batch
                ]

                # Add header embed for first batch
                if i == 0:
                    header_embed = {
                        "title": f"🚨 {title}",
                        "description": f"Found **{len(vulnerabilities)}** new vulnerabilities",
                        "color": 0xFF0000,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                    embeds.insert(0, header_embed)

                payload = {
                    "username": "AutoBug Security Alert",
                    "embeds": embeds,
                }

                response = await self.client.post(self.webhook_url, json=payload)
                response.raise_for_status()

                # Rate limit protection (Discord allows 5 requests per 2 seconds)
                if i + batch_size < len(vulnerabilities):
                    await asyncio.sleep(0.5)

            logger.info(f"Sent batch Discord alert for {len(vulnerabilities)} vulnerabilities")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send batch Discord alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending batch Discord alert: {e}")
            return False

    async def send_summary(
        self,
        title: str,
        description: str,
        stats: Dict,
        alert_type: AlertType = AlertType.DAILY_SUMMARY,
    ) -> bool:
        """
        Send summary report to Discord.
        
        Args:
            title: Summary title
            description: Summary description
            stats: Statistics dictionary
            alert_type: Type of alert
            
        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
            return False

        try:
            embed = self._build_summary_embed(title, description, stats, alert_type)
            
            payload = {
                "username": "AutoBug Report",
                "embeds": [embed],
            }

            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            logger.info(f"Sent Discord summary: {title}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send Discord summary: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord summary: {e}")
            return False

    async def send_custom_message(
        self,
        title: str,
        description: str,
        fields: Optional[List[Dict]] = None,
        color: int = 0x5865F2,
    ) -> bool:
        """
        Send custom message to Discord.
        
        Args:
            title: Message title
            description: Message description
            fields: Optional list of embed fields
            color: Embed color
            
        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Discord webhook URL not configured")
            return False

        try:
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "fields": fields or [],
                "timestamp": datetime.utcnow().isoformat(),
            }

            payload = {
                "username": "AutoBug",
                "embeds": [embed],
            }

            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            logger.info(f"Sent Discord custom message: {title}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send Discord message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Discord message: {e}")
            return False

    async def test_connection(self) -> bool:
        """
        Test Discord webhook connection.
        
        Returns:
            True if successful, False otherwise
        """
        return await self.send_custom_message(
            title="🧪 Test Alert",
            description="Discord webhook is configured correctly!",
            fields=[
                {"name": "Status", "value": "✅ Connected", "inline": True},
                {"name": "Time", "value": f"<t:{int(datetime.utcnow().timestamp())}:F>", "inline": True},
            ],
            color=0x00FF00,
        )
