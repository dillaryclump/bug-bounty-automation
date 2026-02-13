"""
Slack Alert Client
Sends notifications to Slack via webhooks using Block Kit.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional

import httpx

from src.config import settings
from src.db.models import Alert, AlertType, SeverityLevel, Vulnerability
from src.utils.logging import get_logger

logger = get_logger(__name__)


class SlackAlertClient:
    """Client for sending alerts to Slack via webhooks."""

    # Severity emojis for Slack
    SEVERITY_EMOJIS = {
        SeverityLevel.CRITICAL: ":rotating_light:",
        SeverityLevel.HIGH: ":warning:",
        SeverityLevel.MEDIUM: ":large_orange_diamond:",
        SeverityLevel.LOW: ":large_blue_diamond:",
        SeverityLevel.INFO: ":information_source:",
    }

    # Alert type emojis
    ALERT_EMOJIS = {
        AlertType.NEW_VULNERABILITY: ":bug:",
        AlertType.CRITICAL_FINDING: ":rotating_light:",
        AlertType.NEW_ASSET: ":new:",
        AlertType.SCOPE_CHANGE: ":dart:",
        AlertType.DAILY_SUMMARY: ":bar_chart:",
        AlertType.WEEKLY_DIGEST: ":chart_with_upwards_trend:",
        AlertType.SCAN_COMPLETE: ":white_check_mark:",
        AlertType.SCAN_FAILED: ":x:",
    }

    # Color coding for Slack attachments
    COLORS = {
        SeverityLevel.CRITICAL: "#FF0000",  # Red
        SeverityLevel.HIGH: "#FF8C00",      # Dark Orange
        SeverityLevel.MEDIUM: "#FFD700",    # Gold
        SeverityLevel.LOW: "#87CEEB",       # Sky Blue
        SeverityLevel.INFO: "#808080",      # Gray
    }

    def __init__(self, webhook_url: Optional[str] = None):
        """
        Initialize Slack client.
        
        Args:
            webhook_url: Slack webhook URL (defaults to settings)
        """
        self.webhook_url = webhook_url or settings.slack_webhook_url
        self.client = httpx.AsyncClient(timeout=30.0)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()

    def _get_severity_emoji(self, severity: Optional[SeverityLevel]) -> str:
        """Get emoji for severity level."""
        return self.SEVERITY_EMOJIS.get(severity, ":speech_balloon:")

    def _get_alert_emoji(self, alert_type: AlertType) -> str:
        """Get emoji for alert type."""
        return self.ALERT_EMOJIS.get(alert_type, ":mega:")

    def _get_severity_color(self, severity: Optional[SeverityLevel]) -> str:
        """Get Slack color for severity level."""
        return self.COLORS.get(severity, "#808080")

    def _build_vulnerability_blocks(
        self,
        vuln: Vulnerability,
        alert_type: AlertType = AlertType.NEW_VULNERABILITY,
    ) -> List[Dict]:
        """
        Build Slack blocks for vulnerability alert.
        
        Args:
            vuln: Vulnerability object
            alert_type: Type of alert
            
        Returns:
            List of Slack block dictionaries
        """
        emoji = self._get_alert_emoji(alert_type)
        severity_emoji = self._get_severity_emoji(vuln.severity)

        blocks = [
            # Header
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {vuln.name[:150]}",  # Slack limits header text
                    "emoji": True,
                },
            },
            # Matched URL
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Matched At:* <{vuln.matched_at}|{vuln.matched_at}>",
                },
            },
            # Severity and template
            {
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Severity:*\n{severity_emoji} `{vuln.severity.value.upper()}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*Template:*\n`{vuln.template_id}`",
                    },
                ],
            },
        ]

        # Asset info
        if vuln.asset:
            blocks.append({
                "type": "section",
                "fields": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Asset:*\n`{vuln.asset.value}`",
                    },
                    {
                        "type": "mrkdwn",
                        "text": f"*First Seen:*\n<!date^{int(vuln.first_seen.timestamp())}^{{date_short_pretty}} {{time}}|{vuln.first_seen}>",
                    },
                ],
            })

        # Tags
        if vuln.tags:
            tags_str = ", ".join([f"`{tag}`" for tag in vuln.tags[:10]])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Tags:*\n{tags_str}",
                },
            })

        # Curl command
        if vuln.curl_command:
            curl = vuln.curl_command
            if len(curl) > 2000:  # Slack block text limit
                curl = curl[:1997] + "..."
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Reproduction:*\n```{curl}```",
                },
            })

        # Divider
        blocks.append({"type": "divider"})

        return blocks

    def _build_summary_blocks(
        self,
        title: str,
        description: str,
        stats: Dict,
        alert_type: AlertType = AlertType.DAILY_SUMMARY,
    ) -> List[Dict]:
        """
        Build Slack blocks for summary reports.
        
        Args:
            title: Summary title
            description: Summary description
            stats: Statistics dictionary
            alert_type: Type of alert
            
        Returns:
            List of Slack block dictionaries
        """
        emoji = self._get_alert_emoji(alert_type)

        blocks = [
            # Header
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{emoji} {title}",
                    "emoji": True,
                },
            },
            # Description
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": description,
                },
            },
            {"type": "divider"},
        ]

        # Add stats as fields (max 10 fields per section)
        stat_items = list(stats.items())
        for i in range(0, len(stat_items), 10):
            batch = stat_items[i:i + 10]
            fields = []
            for key, value in batch:
                fields.append({
                    "type": "mrkdwn",
                    "text": f"*{key}:*\n{value}",
                })
            blocks.append({
                "type": "section",
                "fields": fields,
            })

        return blocks

    async def send_vulnerability_alert(
        self,
        vulnerability: Vulnerability,
        alert_type: AlertType = AlertType.NEW_VULNERABILITY,
    ) -> bool:
        """
        Send vulnerability alert to Slack.
        
        Args:
            vulnerability: Vulnerability to alert on
            alert_type: Type of alert
            
        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        try:
            blocks = self._build_vulnerability_blocks(vulnerability, alert_type)
            
            # Also include color-coded attachment for visual distinction
            payload = {
                "blocks": blocks,
                "attachments": [{
                    "color": self._get_severity_color(vulnerability.severity),
                    "fallback": f"{vulnerability.severity.value.upper()}: {vulnerability.name}",
                }],
            }

            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            logger.info(f"Sent Slack alert for vulnerability {vulnerability.id}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack alert: {e}")
            return False

    async def send_batch_vulnerabilities(
        self,
        vulnerabilities: List[Vulnerability],
        title: str = "New Vulnerabilities Detected",
    ) -> bool:
        """
        Send batch of vulnerabilities to Slack.
        
        Args:
            vulnerabilities: List of vulnerabilities
            title: Message title
            
        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        if not vulnerabilities:
            return True

        try:
            # Slack messages limited to 50 blocks, so send in batches
            # Each vuln uses ~4-6 blocks, so batch ~8 at a time
            batch_size = 8
            
            for i in range(0, len(vulnerabilities), batch_size):
                batch = vulnerabilities[i:i + batch_size]
                
                # Header blocks for first message
                if i == 0:
                    blocks = [
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f":rotating_light: {title}",
                                "emoji": True,
                            },
                        },
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"Found *{len(vulnerabilities)}* new vulnerabilities",
                            },
                        },
                        {"type": "divider"},
                    ]
                else:
                    blocks = []

                # Add vulnerability blocks
                for vuln in batch:
                    vuln_blocks = self._build_vulnerability_blocks(vuln)
                    blocks.extend(vuln_blocks)

                payload = {"blocks": blocks}

                response = await self.client.post(self.webhook_url, json=payload)
                response.raise_for_status()

                # Rate limit protection
                if i + batch_size < len(vulnerabilities):
                    await asyncio.sleep(1)

            logger.info(f"Sent batch Slack alert for {len(vulnerabilities)} vulnerabilities")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send batch Slack alert: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending batch Slack alert: {e}")
            return False

    async def send_summary(
        self,
        title: str,
        description: str,
        stats: Dict,
        alert_type: AlertType = AlertType.DAILY_SUMMARY,
    ) -> bool:
        """
        Send summary report to Slack.
        
        Args:
            title: Summary title
            description: Summary description
            stats: Statistics dictionary
            alert_type: Type of alert
            
        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

        try:
            blocks = self._build_summary_blocks(title, description, stats, alert_type)
            
            payload = {"blocks": blocks}

            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            logger.info(f"Sent Slack summary: {title}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send Slack summary: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack summary: {e}")
            return False

    async def send_custom_message(
        self,
        title: str,
        description: str,
        fields: Optional[Dict[str, str]] = None,
    ) -> bool:
        """
        Send custom message to Slack.
        
        Args:
            title: Message title
            description: Message description
            fields: Optional dictionary of field name -> value pairs
            
        Returns:
            True if successful, False otherwise
        """
        if not self.webhook_url:
            logger.warning("Slack webhook URL not configured")
            return False

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
                        "text": description,
                    },
                },
            ]

            if fields:
                field_blocks = []
                for name, value in fields.items():
                    field_blocks.append({
                        "type": "mrkdwn",
                        "text": f"*{name}:*\n{value}",
                    })
                blocks.append({
                    "type": "section",
                    "fields": field_blocks,
                })

            payload = {"blocks": blocks}

            response = await self.client.post(self.webhook_url, json=payload)
            response.raise_for_status()

            logger.info(f"Sent Slack custom message: {title}")
            return True

        except httpx.HTTPError as e:
            logger.error(f"Failed to send Slack message: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending Slack message: {e}")
            return False

    async def test_connection(self) -> bool:
        """
        Test Slack webhook connection.
        
        Returns:
            True if successful, False otherwise
        """
        return await self.send_custom_message(
            title=":test_tube: Test Alert",
            description="Slack webhook is configured correctly!",
            fields={
                "Status": ":white_check_mark: Connected",
                "Time": f"<!date^{int(datetime.utcnow().timestamp())}^{{date_short_pretty}} {{time}}|Now>",
            },
        )
