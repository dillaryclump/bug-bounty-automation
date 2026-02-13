"""
CLI commands for vulnerability scanning.
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.db.repositories import ProgramRepository, VulnerabilityRepository
from src.db.session import db_manager
from src.utils.logging import get_logger, setup_logging
from src.workflows.vulnerability_scan import vulnerability_scan_flow

vuln_app = typer.Typer(name="vuln", help="Vulnerability scanning commands")
console = Console()
logger = get_logger(__name__)


@vuln_app.command("scan")
def run_vuln_scan(
    program_id: int = typer.Argument(..., help="Program ID to scan for vulnerabilities"),
    force: bool = typer.Option(False, "--force", "-f", help="Force rescan all assets"),
    no_oob: bool = typer.Option(False, "--no-oob", help="Disable Interactsh OOB detection"),
) -> None:
    """Run vulnerability scan using Nuclei."""
    setup_logging()
    
    console.print("[bold green]🔍 Starting Vulnerability Scan[/bold green]")
    console.print(f"Program ID: {program_id}")
    console.print(f"OOB Detection: {'Disabled' if no_oob else 'Enabled'}")
    console.print()
    
    async def _run() -> None:
        # Verify program exists
        async with db_manager.get_session() as session:
            repo = ProgramRepository(session)
            program = await repo.get_by_id(program_id)
            
            if not program:
                console.print(f"[red]❌ Program {program_id} not found[/red]")
                return
            
            console.print(f"Target: [cyan]{program.program_name}[/cyan]")
            console.print()
        
        # Run vulnerability scan
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Scanning for vulnerabilities...", total=None)
            
            result = await vulnerability_scan_flow(
                program_id,
                force_rescan=force,
                enable_interactsh=not no_oob,
            )
            
            progress.update(task, completed=True)
        
        # Display results
        if result.get("status") == "no_scan_needed":
            console.print("[yellow]ℹ️  All assets are up to date, no scan needed[/yellow]")
            console.print("   Run with --force to rescan anyway")
            return
        
        console.print()
        console.print("[bold green]✅ Vulnerability Scan Complete![/bold green]")
        console.print(f"Duration: {result.get('duration_seconds', 0):.1f}s")
        console.print(f"Targets Scanned: {result.get('targets_scanned', 0)}")
        console.print(f"Total Findings: {result.get('total_findings', 0)}")
        console.print(f"New Vulnerabilities: [green]{result.get('unique_findings', 0)}[/green]")
        
        # Severity breakdown table
        severity_counts = result.get("severity_breakdown", {})
        if any(severity_counts.values()):
            console.print()
            table = Table(title="Severity Breakdown")
            table.add_column("Severity", style="bold")
            table.add_column("Count", justify="right")
            
            severity_styles = {
                "critical": "red bold",
                "high": "red",
                "medium": "yellow",
                "low": "blue",
                "info": "white",
            }
            
            for severity in ["critical", "high", "medium", "low", "info"]:
                count = severity_counts.get(severity, 0)
                if count > 0:
                    table.add_row(
                        severity.upper(),
                        str(count),
                        style=severity_styles.get(severity, "white"),
                    )
            
            console.print(table)
        
        if result.get("oob_interactions", 0) > 0:
            console.print(f"\n🌐 OOB Interactions Detected: {result['oob_interactions']}")
    
    asyncio.run(_run())


@vuln_app.command("list")
def list_vulnerabilities(
    program_id: Optional[int] = typer.Option(None, "--program", "-p", help="Filter by program ID"),
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="Filter by severity (critical/high/medium/low/info)"),
    limit: int = typer.Option(50, "--limit", "-l", help="Max results to show"),
    new_only: bool = typer.Option(False, "--new", help="Show only new (unreported) vulnerabilities"),
) -> None:
    """List discovered vulnerabilities."""
    setup_logging()
    
    async def _list() -> None:
        async with db_manager.get_session() as session:
            vuln_repo = VulnerabilityRepository(session)
            
            if new_only:
                from src.db.models import SeverityLevel
                min_sev = SeverityLevel.MEDIUM
                if severity:
                    min_sev = SeverityLevel[severity.upper()]
                
                vulns = await vuln_repo.get_new_vulnerabilities(min_severity=min_sev)
            else:
                # For now, get all - TODO: add filtering methods to repo
                console.print("[yellow]Note: Full vulnerability filtering coming soon[/yellow]")
                vulns = await vuln_repo.get_new_vulnerabilities()
            
            if not vulns:
                console.print("[yellow]No vulnerabilities found[/yellow]")
                return
            
            # Limit results
            vulns = vulns[:limit]
            
            # Display table
            table = Table(title=f"Vulnerabilities ({len(vulns)} shown)")
            table.add_column("ID", style="cyan")
            table.add_column("Severity", style="bold")
            table.add_column("Name")
            table.add_column("Asset")
            table.add_column("Template")
            table.add_column("Found")
            
            severity_styles = {
                "critical": "red bold",
                "high": "red",
                "medium": "yellow",
                "low": "blue",
                "info": "white",
            }
            
            for vuln in vulns:
                # Truncate long names
                name = vuln.name[:50] + "..." if len(vuln.name) > 50 else vuln.name
                template = vuln.template_id[:30] + "..." if len(vuln.template_id) > 30 else vuln.template_id
                
                # Extract domain from matched_at
                asset_url = vuln.matched_at.split("/")[2] if "/" in vuln.matched_at else vuln.matched_at
                
                table.add_row(
                    str(vuln.id),
                    vuln.severity.value.upper(),
                    name,
                    asset_url[:40],
                    template,
                    vuln.first_seen.strftime("%Y-%m-%d %H:%M"),
                    style=severity_styles.get(vuln.severity.value, "white"),
                )
            
            console.print(table)
            
            if len(vulns) == limit:
                console.print(f"\n[yellow]Showing first {limit} results. Use --limit to see more.[/yellow]")
    
    asyncio.run(_list())


@vuln_app.command("show")
def show_vulnerability(
    vuln_id: int = typer.Argument(..., help="Vulnerability ID to show details"),
) -> None:
    """Show detailed information about a vulnerability."""
    setup_logging()
    
    async def _show() -> None:
        async with db_manager.get_session() as session:
            from sqlalchemy import select
            from src.db.models import Vulnerability
            
            result = await session.execute(
                select(Vulnerability).where(Vulnerability.id == vuln_id)
            )
            vuln = result.scalar_one_or_none()
            
            if not vuln:
                console.print(f"[red]Vulnerability {vuln_id} not found[/red]")
                return
            
            # Display details
            console.print(f"\n[bold]Vulnerability #{vuln.id}[/bold]")
            console.print("=" * 70)
            console.print(f"Name: {vuln.name}")
            console.print(f"Severity: [{vuln.severity.value.upper()}]", style="bold")
            console.print(f"Template: {vuln.template_id}")
            console.print(f"Matched At: {vuln.matched_at}")
            console.print(f"First Seen: {vuln.first_seen}")
            console.print(f"Last Seen: {vuln.last_seen}")
            
            if vuln.tags:
                console.print(f"Tags: {', '.join(vuln.tags)}")
            
            if vuln.reference:
                console.print(f"References:")
                for ref in vuln.reference[:5]:  # Show first 5
                    console.print(f"  - {ref}")
            
            if vuln.extracted_results:
                console.print(f"\nExtracted Results:")
                for result in vuln.extracted_results[:5]:
                    console.print(f"  - {result}")
            
            if vuln.curl_command:
                console.print(f"\nCurl Command:")
                console.print(f"  {vuln.curl_command}")
            
            console.print(f"\nStatus:")
            console.print(f"  New: {vuln.is_new}")
            console.print(f"  Verified: {vuln.verified}")
            console.print(f"  Reported: {vuln.reported}")
            console.print(f"  False Positive: {vuln.false_positive}")
            
            console.print("=" * 70)
    
    asyncio.run(_show())


@vuln_app.command("mark-reported")
def mark_as_reported(
    vuln_ids: str = typer.Argument(..., help="Comma-separated vulnerability IDs (e.g., 1,2,3)"),
) -> None:
    """Mark vulnerabilities as reported."""
    setup_logging()
    
    async def _mark() -> None:
        ids = [int(x.strip()) for x in vuln_ids.split(",")]
        
        async with db_manager.get_session() as session:
            vuln_repo = VulnerabilityRepository(session)
            await vuln_repo.mark_reported(ids)
            
            console.print(f"[green]✅ Marked {len(ids)} vulnerabilities as reported[/green]")
    
    asyncio.run(_mark())


@vuln_app.command("stats")
def show_statistics(
    program_id: Optional[int] = typer.Option(None, "--program", "-p", help="Filter by program ID"),
) -> None:
    """Show vulnerability statistics."""
    setup_logging()
    
    async def _stats() -> None:
        async with db_manager.get_session() as session:
            from sqlalchemy import select, func
            from src.db.models import Vulnerability, SeverityLevel
            
            # Get total count
            result = await session.execute(select(func.count(Vulnerability.id)))
            total = result.scalar() or 0
            
            # Count by severity
            severity_counts = {}
            for severity in SeverityLevel:
                result = await session.execute(
                    select(func.count(Vulnerability.id)).where(
                        Vulnerability.severity == severity
                    )
                )
                severity_counts[severity.value] = result.scalar() or 0
            
            # Count new/reported
            result = await session.execute(
                select(func.count(Vulnerability.id)).where(Vulnerability.is_new == True)
            )
            new_count = result.scalar() or 0
            
            result = await session.execute(
                select(func.count(Vulnerability.id)).where(Vulnerability.reported == True)
            )
            reported_count = result.scalar() or 0
            
            # Display
            console.print("\n[bold]Vulnerability Statistics[/bold]")
            console.print("=" * 50)
            console.print(f"Total Vulnerabilities: {total}")
            console.print(f"New (Unreported): {new_count}")
            console.print(f"Reported: {reported_count}")
            console.print()
            
            table = Table(title="Severity Breakdown")
            table.add_column("Severity", style="bold")
            table.add_column("Count", justify="right")
            table.add_column("Percentage", justify="right")
            
            for severity in ["critical", "high", "medium", "low", "info"]:
                count = severity_counts.get(severity, 0)
                pct = (count / total * 100) if total > 0 else 0
                table.add_row(
                    severity.upper(),
                    str(count),
                    f"{pct:.1f}%",
                )
            
            console.print(table)
    
    asyncio.run(_stats())


if __name__ == "__main__":
    vuln_app()
