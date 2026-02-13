"""
CLI tool for managing AutoBug platform.
Uses Typer for beautiful command-line interface.
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.config import settings
from src.db.session import db_manager
from src.db.repositories import ProgramRepository
from src.utils.logging import setup_logging, get_logger
from src.cli_scan import scan_app
from src.cli_vuln import vuln_app
from src.cli_alert import alert_app
from src.cli_scope import scope_app

app = typer.Typer(
    name="autobug",
    help="AutoBug - Automated Bug Bounty Platform CLI",
    add_completion=False,
)
app.add_typer(scan_app, name="scan")
app.add_typer(vuln_app, name="vuln")
app.add_typer(alert_app, name="alert")
app.add_typer(scope_app, name="scope")
console = Console()
logger = get_logger(__name__)


@app.command()
def init() -> None:
    """Initialize the database and create tables."""
    setup_logging()
    console.print("[bold green]Initializing AutoBug database...[/bold green]")
    
    async def _init() -> None:
        await db_manager.create_tables()
        console.print("✅ Database tables created successfully!")
    
    asyncio.run(_init())


@app.command()
def add_program(
    platform: str = typer.Option(..., "--platform", "-p", help="Platform (hackerone/bugcrowd)"),
    handle: str = typer.Option(..., "--handle", "-h", help="Program handle"),
    name: str = typer.Option(..., "--name", "-n", help="Program name"),
) -> None:
    """Add a new bug bounty program to monitor."""
    setup_logging()
    
    async def _add_program() -> None:
        async with db_manager.get_session() as session:
            repo = ProgramRepository(session)
            
            # Check if already exists
            existing = await repo.get_by_handle(platform, handle)
            if existing:
                console.print(f"[yellow]Program already exists: {handle}[/yellow]")
                return
            
            program = await repo.create(
                platform=platform,
                program_handle=handle,
                program_name=name,
            )
            console.print(f"✅ Added program: [bold]{name}[/bold] ({handle})")
    
    asyncio.run(_add_program())


@app.command()
def list_programs() -> None:
    """List all monitored programs."""
    setup_logging()
    
    async def _list_programs() -> None:
        async with db_manager.get_session() as session:
            repo = ProgramRepository(session)
            programs = await repo.get_active_programs()
            
            if not programs:
                console.print("[yellow]No programs found. Add one with 'add-program'[/yellow]")
                return
            
            table = Table(title="Bug Bounty Programs")
            table.add_column("ID", style="cyan")
            table.add_column("Platform", style="magenta")
            table.add_column("Handle", style="green")
            table.add_column("Name", style="blue")
            table.add_column("Active", style="yellow")
            
            for prog in programs:
                table.add_row(
                    str(prog.id),
                    prog.platform,
                    prog.program_handle,
                    prog.program_name,
                    "✓" if prog.is_active else "✗",
                )
            
            console.print(table)
    
    asyncio.run(_list_programs())


@app.command()
def status() -> None:
    """Show platform status and statistics."""
    console.print("[bold]AutoBug Platform Status[/bold]")
    console.print(f"Environment: {settings.environment}")
    console.print(f"Database: {settings.database_url}")
    console.print(f"Redis: {settings.redis_url}")





@app.command()
def version() -> None:
    """Show version information."""
    console.print(f"[bold]{settings.app_name}[/bold] v0.1.0")
    console.print("Built with ❤️  for bug bounty hunters")


if __name__ == "__main__":
    app()
