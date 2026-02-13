"""
CLI commands for running scans and workflows.
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.db.session import db_manager
from src.db.repositories import ProgramRepository
from src.utils.logging import setup_logging, get_logger
from src.workflows.reconnaissance import reconnaissance_flow, quick_recon_flow

scan_app = typer.Typer(name="scan", help="Scan management commands")
console = Console()
logger = get_logger(__name__)


@scan_app.command("full")
def run_full_scan(
    program_id: int = typer.Argument(..., help="Program ID to scan"),
    force: bool = typer.Option(False, "--force", "-f", help="Force full rescan"),
) -> None:
    """Run full reconnaissance scan (subdomain enum + HTTP probing)."""
    setup_logging()
    
    console.print(f"[bold green]🚀 Starting full reconnaissance scan[/bold green]")
    console.print(f"Program ID: {program_id}")
    
    async def _run() -> None:
        # Verify program exists
        async with db_manager.get_session() as session:
            repo = ProgramRepository(session)
            program = await repo.get_by_id(program_id)
            
            if not program:
                console.print(f"[red]❌ Program {program_id} not found[/red]")
                return
            
            console.print(f"Target: [cyan]{program.program_name}[/cyan]")
            console.print(f"Scope: {', '.join(program.in_scope or [])}")
            console.print()
        
        # Run workflow
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Running reconnaissance...", total=None)
            
            result = await reconnaissance_flow(program_id, force_full_scan=force)
            
            progress.update(task, completed=True)
        
        # Display results
        if "error" in result:
            console.print(f"[red]❌ {result['error']}[/red]")
        else:
            console.print()
            console.print("[bold green]✅ Scan Complete![/bold green]")
            console.print(f"Duration: {result.get('duration_seconds', 0):.1f}s")
            console.print(f"Subdomains Found: {result.get('subdomains_found', 0)}")
            console.print(f"HTTP Endpoints: {result.get('http_endpoints', 0)}")
            console.print(f"New Assets: [green]{result.get('new_assets', 0)}[/green]")
            console.print(f"Modified Assets: [yellow]{result.get('modified_assets', 0)}[/yellow]")
            console.print(f"Unchanged Assets: {result.get('unchanged_assets', 0)}")
    
    asyncio.run(_run())


@scan_app.command("quick")
def run_quick_scan(
    program_id: int = typer.Argument(..., help="Program ID to scan"),
) -> None:
    """Run quick scan (HTTP probing of known assets only)."""
    setup_logging()
    
    console.print(f"[bold cyan]⚡ Quick scan starting...[/bold cyan]")
    
    async def _run() -> None:
        result = await quick_recon_flow(program_id)
        
        if "error" in result:
            console.print(f"[red]❌ {result['error']}[/red]")
        else:
            console.print("[green]✅ Quick scan complete![/green]")
            console.print(f"Modified Assets: {result.get('modified_assets', 0)}")
            console.print(f"Total Changes: {result.get('total_changes', 0)}")
    
    asyncio.run(_run())


@scan_app.command("test-tools")
def test_scanning_tools() -> None:
    """Test if scanning tools are installed and working."""
    setup_logging()
    
    console.print("[bold]🔧 Testing Scanning Tools[/bold]\n")
    
    async def _test() -> None:
        from src.scanners.subfinder import SubfinderScanner
        from src.scanners.httpx_scanner import HttpxScanner
        from src.scanners.naabu import NaabuScanner
        from src.scanners.dns_resolver import DnsResolver
        
        tools = [
            ("Subfinder", SubfinderScanner),
            ("httpx", HttpxScanner),
            ("Naabu", NaabuScanner),
            ("puredns", DnsResolver),
        ]
        
        for name, scanner_class in tools:
            try:
                scanner = scanner_class()
                info = await scanner.check_installation()
                
                if info.get("installed"):
                    console.print(f"✅ {name}: [green]Installed[/green]")
                    console.print(f"   Path: {info.get('path', 'N/A')}")
                    version = info.get('version', '').split('\n')[0]
                    if version:
                        console.print(f"   Version: {version}")
                else:
                    console.print(f"❌ {name}: [red]Not Installed[/red]")
                    console.print(f"   Error: {info.get('error', 'Unknown')}")
            except Exception as e:
                console.print(f"❌ {name}: [red]Error[/red] - {e}")
            
            console.print()
    
    asyncio.run(_test())


if __name__ == "__main__":
    scan_app()
