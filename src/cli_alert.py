"""
Alert Management CLI Commands
Commands for configuring, testing, and managing alerts.
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.config import settings
from src.db.models import AlertType
from src.db.session import db_manager
from src.alerting.manager import AlertManager, AlertRepository
from src.workflows.alerting import (
    test_alerts_flow,
    daily_summary_report_flow,
    weekly_digest_report_flow,
    retry_failed_alerts_flow,
)
from src.utils.logging import get_logger

alert_app = typer.Typer(help="Alert management commands")
console = Console()
logger = get_logger(__name__)


@alert_app.command("test")
def test_alerts():
    """
    Test all configured alert channels.
    Sends a test message to Discord and/or Slack.
    """
    console.print("\n[bold cyan]🧪 Testing Alert Channels[/bold cyan]\n")
    
    # Check configuration
    if not settings.discord_webhook_url and not settings.slack_webhook_url:
        console.print("[red]❌ No alert channels configured![/red]")
        console.print("\nConfigure in .env:")
        console.print("  DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...")
        console.print("  SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...")
        raise typer.Exit(1)
    
    # Show config
    console.print("[bold]Configured Channels:[/bold]")
    if settings.discord_webhook_url:
        console.print(f"  ✅ Discord: {settings.discord_webhook_url[:50]}...")
    if settings.slack_webhook_url:
        console.print(f"  ✅ Slack: {settings.slack_webhook_url[:50]}...")
    console.print()
    
    # Run test
    results = asyncio.run(test_alerts_flow())
    
    # Display results
    console.print("\n[bold]Test Results:[/bold]")
    for channel, success in results.items():
        if success:
            console.print(f"  [green]✅ {channel.title()}: Success[/green]")
        else:
            console.print(f"  [red]❌ {channel.title()}: Failed[/red]")
    
    console.print()


@alert_app.command("config")
def show_config():
    """Show current alert configuration."""
    console.print("\n[bold cyan]⚙️  Alert Configuration[/bold cyan]\n")
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="cyan")
    table.add_column("Value", style="white")
    
    # Channels
    table.add_row(
        "Discord Webhook",
        "✅ Configured" if settings.discord_webhook_url else "❌ Not set"
    )
    table.add_row(
        "Slack Webhook",
        "✅ Configured" if settings.slack_webhook_url else "❌ Not set"
    )
    
    table.add_section()
    
    # Settings
    table.add_row("Min Severity", settings.alert_min_severity.upper())
    table.add_row("Critical Channel", settings.alert_critical_channel)
    table.add_row("Batch Window", f"{settings.alert_batch_window}s")
    table.add_row(
        "Daily Summary",
        f"{'✅' if settings.enable_daily_summary else '❌'} {settings.daily_summary_time} UTC"
    )
    table.add_row(
        "Weekly Digest",
        f"{'✅' if settings.enable_weekly_digest else '❌'} {settings.weekly_digest_day.title()}"
    )
    
    console.print(table)
    console.print()


@alert_app.command("daily-summary")
def send_daily_summary(
    program_id: Optional[int] = typer.Option(None, "--program", "-p", help="Filter by program ID"),
):
    """Send daily summary report."""
    console.print("\n[bold cyan]📊 Sending Daily Summary[/bold cyan]\n")
    
    if not settings.discord_webhook_url and not settings.slack_webhook_url:
        console.print("[red]❌ No alert channels configured![/red]")
        raise typer.Exit(1)
    
    success = asyncio.run(daily_summary_report_flow(program_id))
    
    if success:
        console.print("[green]✅ Daily summary sent successfully![/green]\n")
    else:
        console.print("[red]❌ Failed to send daily summary[/red]\n")
        raise typer.Exit(1)


@alert_app.command("weekly-digest")
def send_weekly_digest(
    program_id: Optional[int] = typer.Option(None, "--program", "-p", help="Filter by program ID"),
):
    """Send weekly digest report."""
    console.print("\n[bold cyan]📈 Sending Weekly Digest[/bold cyan]\n")
    
    if not settings.discord_webhook_url and not settings.slack_webhook_url:
        console.print("[red]❌ No alert channels configured![/red]")
        raise typer.Exit(1)
    
    success = asyncio.run(weekly_digest_report_flow(program_id))
    
    if success:
        console.print("[green]✅ Weekly digest sent successfully![/green]\n")
    else:
        console.print("[red]❌ Failed to send weekly digest[/red]\n")
        raise typer.Exit(1)


@alert_app.command("history")
def show_alert_history(
    hours: int = typer.Option(24, "--hours", "-h", help="Hours to look back"),
    program_id: Optional[int] = typer.Option(None, "--program", "-p", help="Filter by program ID"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max alerts to show"),
):
    """Show recent alert history."""
    console.print(f"\n[bold cyan]📜 Alert History (Last {hours} hours)[/bold cyan]\n")
    
    async def get_history():
        async with db_manager.get_session() as session:
            repo = AlertRepository(session)
            alerts = await repo.get_recent_alerts(hours=hours, program_id=program_id)
            return alerts[:limit]
    
    alerts = asyncio.run(get_history())
    
    if not alerts:
        console.print("[yellow]No alerts found in the specified time period[/yellow]\n")
        return
    
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("Type", style="yellow", width=20)
    table.add_column("Title", style="white", width=40)
    table.add_column("Channel", style="blue", width=10)
    table.add_column("Status", style="green", width=10)
    table.add_column("Time", style="dim", width=20)
    
    for alert in alerts:
        status = "✅ Sent" if alert.success else ("❌ Failed" if alert.sent else "⏳ Pending")
        
        table.add_row(
            str(alert.id),
            alert.alert_type.value,
            alert.title[:40] + "..." if len(alert.title) > 40 else alert.title,
            alert.channel,
            status,
            alert.created_at.strftime("%Y-%m-%d %H:%M"),
        )
    
    console.print(table)
    console.print(f"\n[dim]Showing {len(alerts)} alerts[/dim]\n")


@alert_app.command("stats")
def show_alert_stats(
    days: int = typer.Option(7, "--days", "-d", help="Days to analyze"),
    program_id: Optional[int] = typer.Option(None, "--program", "-p", help="Filter by program ID"),
):
    """Show alert statistics."""
    console.print(f"\n[bold cyan]📈 Alert Statistics (Last {days} days)[/bold cyan]\n")
    
    async def get_stats():
        async with db_manager.get_session() as session:
            repo = AlertRepository(session)
            return await repo.get_stats(days=days, program_id=program_id)
    
    stats = asyncio.run(get_stats())
    
    # Summary table
    summary_table = Table(show_header=True, header_style="bold magenta", title="Overview")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Count", style="white", justify="right")
    
    summary_table.add_row("Total Alerts", str(stats["total_alerts"]))
    summary_table.add_row("Successful", f"[green]{stats['successful']}[/green]")
    summary_table.add_row("Failed", f"[red]{stats['failed']}[/red]")
    summary_table.add_row("Pending", f"[yellow]{stats['pending']}[/yellow]")
    
    console.print(summary_table)
    console.print()
    
    # By type
    if stats["by_type"]:
        type_table = Table(show_header=True, header_style="bold magenta", title="By Alert Type")
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Count", style="white", justify="right")
        
        for alert_type, count in sorted(stats["by_type"].items(), key=lambda x: x[1], reverse=True):
            type_table.add_row(alert_type, str(count))
        
        console.print(type_table)
        console.print()
    
    # By channel
    if stats["by_channel"]:
        channel_table = Table(show_header=True, header_style="bold magenta", title="By Channel")
        channel_table.add_column("Channel", style="cyan")
        channel_table.add_column("Count", style="white", justify="right")
        
        for channel, count in sorted(stats["by_channel"].items(), key=lambda x: x[1], reverse=True):
            channel_table.add_row(channel, str(count))
        
        console.print(channel_table)
        console.print()


@alert_app.command("retry-failed")
def retry_failed_alerts(
    max_retries: int = typer.Option(3, "--max-retries", "-m", help="Max retry attempts"),
):
    """Retry failed alert deliveries."""
    console.print("\n[bold cyan]🔄 Retrying Failed Alerts[/bold cyan]\n")
    
    count = asyncio.run(retry_failed_alerts_flow(max_retries))
    
    if count > 0:
        console.print(f"[green]✅ Successfully retried {count} alerts[/green]\n")
    else:
        console.print("[yellow]No failed alerts to retry[/yellow]\n")


@alert_app.command("setup-guide")
def setup_guide():
    """Show guide for setting up alert webhooks."""
    console.print("\n[bold cyan]🔔 Alert Setup Guide[/bold cyan]\n")
    
    console.print("[bold]1. Discord Webhook Setup:[/bold]")
    console.print("   a. Open your Discord server")
    console.print("   b. Go to Server Settings → Integrations → Webhooks")
    console.print("   c. Click 'New Webhook'")
    console.print("   d. Name it 'AutoBug Security Alerts'")
    console.print("   e. Select the channel for alerts")
    console.print("   f. Copy the webhook URL")
    console.print("   g. Add to .env: DISCORD_WEBHOOK_URL=<your_url>")
    console.print()
    
    console.print("[bold]2. Slack Webhook Setup:[/bold]")
    console.print("   a. Go to https://api.slack.com/apps")
    console.print("   b. Click 'Create New App' → 'From scratch'")
    console.print("   c. Name it 'AutoBug' and select your workspace")
    console.print("   d. Go to 'Incoming Webhooks' and activate it")
    console.print("   e. Click 'Add New Webhook to Workspace'")
    console.print("   f. Select the channel for alerts")
    console.print("   g. Copy the webhook URL")
    console.print("   h. Add to .env: SLACK_WEBHOOK_URL=<your_url>")
    console.print()
    
    console.print("[bold]3. Configure Alert Settings:[/bold]")
    console.print("   Edit .env file:")
    console.print("   ALERT_MIN_SEVERITY=high         # Minimum severity to alert")
    console.print("   ALERT_CRITICAL_CHANNEL=discord  # Where to send critical alerts")
    console.print("   ENABLE_DAILY_SUMMARY=true       # Daily reports")
    console.print("   DAILY_SUMMARY_TIME=09:00        # Time to send (UTC)")
    console.print()
    
    console.print("[bold]4. Test Your Setup:[/bold]")
    console.print("   python -m src.cli alert test")
    console.print()


if __name__ == "__main__":
    alert_app()
