"""
Scope CLI Commands
Command-line interface for scope monitoring.
"""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from src.db import get_session
from src.db.models import Program, ScopeHistory
from src.scope import ScopeParserFactory, ScopeValidator
from src.workflows.scope_monitoring import (
    monitor_program_scope_flow,
    monitor_all_programs_scope_flow,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

scope_app = typer.Typer(help="Scope monitoring commands")
console = Console()


@scope_app.command("check")
def check_scope(
    program_id: int = typer.Argument(..., help="Program ID to check"),
    api_token: Optional[str] = typer.Option(None, "--token", help="API token for platform"),
):
    """
    Check program scope for changes.
    
    Fetches current scope, compares with previous snapshot,
    and saves the new data.
    """
    console.print(f"[bold blue]Checking scope for program {program_id}...[/bold blue]")
    
    async def run():
        result = await monitor_program_scope_flow(
            program_id=program_id,
            api_token=api_token,
        )
        
        if "error" in result:
            console.print(f"[red]Error: {result['error']}[/red]")
            return
        
        # Display results
        console.print(f"\n[bold green]Program:[/bold green] {result['program_name']}")
        
        comparison = result["comparison"]
        console.print(f"\n[bold]Scope Check Results:[/bold]")
        console.print(f"  Summary: {comparison['summary']}")
        
        if comparison["is_first_check"]:
            console.print("  [yellow]First scope check - baseline established[/yellow]")
        elif comparison["has_changes"]:
            console.print(f"  [yellow]Changes detected:[/yellow]")
            console.print(f"    • Added: {comparison['additions']}")
            console.print(f"    • Removed: {comparison['removals']}")
            console.print(f"    • Modified: {comparison['modifications']}")
            
            # Show individual changes
            if comparison.get("changes"):
                console.print("\n[bold]Change Details:[/bold]")
                for change in comparison["changes"]:
                    symbol = {
                        "added": "+",
                        "removed": "-",
                        "modified": "~",
                    }.get(change["type"], "?")
                    
                    category = change["category"]
                    item = change["item"]
                    
                    console.print(f"  {symbol} [{category}] {item}")
        else:
            console.print("  [green]No changes detected[/green]")
        
        # Show validation results if available
        if result.get("validation"):
            validation = result["validation"]
            console.print(f"\n[bold]Asset Validation:[/bold]")
            console.print(f"  Total assets: {validation['total']}")
            console.print(f"  In scope: {validation['in_scope']}")
            console.print(f"  Out of scope: {validation['out_scope']}")
    
    asyncio.run(run())


@scope_app.command("check-all")
def check_all_scope(
    platform: Optional[str] = typer.Option(None, "--platform", help="Filter by platform"),
    api_token: Optional[str] = typer.Option(None, "--token", help="API token"),
):
    """
    Check scope for all active programs.
    """
    console.print("[bold blue]Checking scope for all programs...[/bold blue]")
    
    async def run():
        result = await monitor_all_programs_scope_flow(
            platform=platform,
            api_token=api_token,
        )
        
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total programs checked: {result['total_programs']}")
        console.print(f"  Programs with changes: {result['programs_with_changes']}")
        
        # Create table
        table = Table(title="Scope Check Results")
        table.add_column("ID", style="cyan")
        table.add_column("Program", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Changes", style="magenta")
        
        for program_result in result["programs"]:
            program_id = str(program_result["program_id"])
            program_name = program_result["program_name"]
            
            if "error" in program_result:
                table.add_row(program_id, program_name, "Error", program_result["error"])
            else:
                comparison = program_result.get("comparison", {})
                if comparison.get("has_changes"):
                    status = "Changed"
                    changes = comparison.get("summary", "")
                else:
                    status = "No changes"
                    changes = "-"
                
                table.add_row(program_id, program_name, status, changes)
        
        console.print(table)
    
    asyncio.run(run())


@scope_app.command("history")
def show_history(
    program_id: int = typer.Argument(..., help="Program ID"),
    limit: int = typer.Option(10, "--limit", help="Number of entries to show"),
):
    """
    Show scope history for a program.
    """
    console.print(f"[bold blue]Scope history for program {program_id}...[/bold blue]")
    
    async def run():
        async with get_session() as session:
            # Get program
            program_result = await session.execute(
                select(Program).where(Program.id == program_id)
            )
            program = program_result.scalar_one_or_none()
            
            if not program:
                console.print("[red]Program not found[/red]")
                return
            
            console.print(f"\n[bold green]Program:[/bold green] {program.name}")
            
            # Get history
            result = await session.execute(
                select(ScopeHistory)
                .where(ScopeHistory.program_id == program_id)
                .order_by(ScopeHistory.checked_at.desc())
                .limit(limit)
            )
            
            history_entries = result.scalars().all()
            
            if not history_entries:
                console.print("[yellow]No history found[/yellow]")
                return
            
            # Create table
            table = Table(title=f"Scope History (last {len(history_entries)} entries)")
            table.add_column("Date", style="cyan")
            table.add_column("In Scope", style="green")
            table.add_column("Out Scope", style="yellow")
            table.add_column("Changes", style="magenta")
            table.add_column("Source", style="blue")
            
            for entry in history_entries:
                date_str = entry.checked_at.strftime("%Y-%m-%d %H:%M")
                in_scope_count = len(entry.in_scope or [])
                out_scope_count = len(entry.out_of_scope or [])
                changes_count = len(entry.changes or [])
                source = entry.source or "unknown"
                
                table.add_row(
                    date_str,
                    str(in_scope_count),
                    str(out_scope_count),
                    str(changes_count) if changes_count > 0 else "-",
                    source,
                )
            
            console.print(table)
    
    asyncio.run(run())


@scope_app.command("validate")
def validate_assets(
    program_id: int = typer.Argument(..., help="Program ID"),
    show_details: bool = typer.Option(False, "--details", help="Show detailed validation results"),
):
    """
    Validate all assets against current program scope.
    """
    console.print(f"[bold blue]Validating assets for program {program_id}...[/bold blue]")
    
    async def run():
        async with get_session() as session:
            # Get program
            program_result = await session.execute(
                select(Program).where(Program.id == program_id)
            )
            program = program_result.scalar_one_or_none()
            
            if not program:
                console.print("[red]Program not found[/red]")
                return
            
            console.print(f"\n[bold green]Program:[/bold green] {program.name}")
            
            # Get latest scope
            scope_result = await session.execute(
                select(ScopeHistory)
                .where(ScopeHistory.program_id == program_id)
                .order_by(ScopeHistory.checked_at.desc())
                .limit(1)
            )
            
            scope_history = scope_result.scalar_one_or_none()
            
            if not scope_history:
                console.print("[red]No scope history found - run 'scope check' first[/red]")
                return
            
            # Create scope data
            from src.scope import ScopeData
            
            scope_data = ScopeData(
                in_scope=scope_history.in_scope or [],
                out_of_scope=scope_history.out_of_scope or [],
                platform=program.platform,
                program_handle=program.handle,
                program_name=program.name,
                program_url=program.url or "",
            )
            
            # Get assets
            from src.db.models import Asset
            
            assets_result = await session.execute(
                select(Asset)
                .where(Asset.program_id == program_id)
                .where(Asset.is_alive == True)
            )
            
            assets = assets_result.scalars().all()
            
            if not assets:
                console.print("[yellow]No assets found[/yellow]")
                return
            
            # Validate
            validator = ScopeValidator(scope_data)
            
            in_scope = []
            out_scope = []
            
            for asset in assets:
                validation = validator.validate(asset.value)
                
                if validation.in_scope:
                    in_scope.append((asset.value, validation))
                else:
                    out_scope.append((asset.value, validation))
            
            # Show summary
            console.print(f"\n[bold]Validation Results:[/bold]")
            console.print(f"  Total assets: {len(assets)}")
            console.print(f"  In scope: {len(in_scope)}")
            console.print(f"  Out of scope: {len(out_scope)}")
            
            # Show details if requested
            if show_details:
                if in_scope:
                    console.print("\n[bold green]In-Scope Assets:[/bold green]")
                    for asset_value, validation in in_scope[:20]:  # Limit to 20
                        console.print(f"  ✓ {asset_value} - {validation.reason}")
                    
                    if len(in_scope) > 20:
                        console.print(f"  ... and {len(in_scope) - 20} more")
                
                if out_scope:
                    console.print("\n[bold red]Out-of-Scope Assets:[/bold red]")
                    for asset_value, validation in out_scope[:20]:  # Limit to 20
                        console.print(f"  ✗ {asset_value} - {validation.reason}")
                    
                    if len(out_scope) > 20:
                        console.print(f"  ... and {len(out_scope) - 20} more")
    
    asyncio.run(run())


@scope_app.command("update")
def update_scope(
    program_id: int = typer.Argument(..., help="Program ID"),
    api_token: Optional[str] = typer.Option(None, "--token", help="API token"),
):
    """
    Manually update program scope (alias for 'check').
    """
    check_scope(program_id, api_token)


if __name__ == "__main__":
    scope_app()
