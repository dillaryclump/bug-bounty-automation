"""
AutoBug Alerting Module
Handles notifications via Discord, Slack, and other channels.
"""

from src.alerting.discord import DiscordAlertClient
from src.alerting.slack import SlackAlertClient
from src.alerting.manager import AlertManager

__all__ = [
    "DiscordAlertClient",
    "SlackAlertClient",
    "AlertManager",
]
