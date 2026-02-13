"""
Example script demonstrating the reconnaissance pipeline.
Run this to test the full workflow end-to-end.
"""

import asyncio
import sys

from src.db.session import db_manager
from src.db.repositories import ProgramRepository, AssetRepository
from src.workflows.reconnaissance import reconnaissance_flow, quick_recon_flow
from src.utils.logging import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


async def create_demo_program() -> int:
    """Create a demo program for testing."""
    logger.info("Creating demo program...")
    
    async with db_manager.get_session() as session:
        repo = ProgramRepository(session)
        
        # Check if demo program exists
        existing = await repo.get_by_handle("demo", "test-program")
        if existing:
            logger.info(f"Demo program already exists with ID: {existing.id}")
            return existing.id
        
        # Create new demo program
        program = await repo.create(
            platform="demo",
            program_handle="test-program",
            program_name="Test Program for AutoBug",
            in_scope=["hackerone.com"],  # Using HackerOne as example (they allow scanning)
            out_of_scope=["test.hackerone.com"],
        )
        
        logger.info(f"✅ Created demo program with ID: {program.id}")
        return program.id


async def run_demo_scan(program_id: int) -> None:
    """Run a demo reconnaissance scan."""
    logger.info("=" * 70)
    logger.info("DEMO: Full Reconnaissance Scan")
    logger.info("=" * 70)
    logger.info(f"Program ID: {program_id}")
    logger.info("")
    
    # Run full reconnaissance
    result = await reconnaissance_flow(program_id, force_full_scan=False)
    
    logger.info("")
    logger.info("=" * 70)
    logger.info("SCAN RESULTS:")
    logger.info("=" * 70)
    
    for key, value in result.items():
        logger.info(f"{key}: {value}")


async def run_demo_quick_scan(program_id: int) -> None:
    """Run a demo quick scan."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("DEMO: Quick Scan (Change Detection)")
    logger.info("=" * 70)
    
    # Run quick scan
    result = await quick_recon_flow(program_id)
    
    logger.info(f"Results: {result}")


async def view_database_results(program_id: int) -> None:
    """View results stored in database."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("DATABASE RESULTS:")
    logger.info("=" * 70)
    
    async with db_manager.get_session() as session:
        asset_repo = AssetRepository(session)
        
        # Get all assets
        assets = await asset_repo.get_by_program(program_id, alive_only=True)
        
        logger.info(f"\nTotal Assets: {len(assets)}")
        logger.info("-" * 70)
        
        # Show first 10 assets
        for asset in assets[:10]:
            logger.info(f"\n🌐 {asset.value}")
            logger.info(f"   Status: {asset.http_status}")
            logger.info(f"   Title: {asset.page_title}")
            logger.info(f"   Technologies: {', '.join(asset.technologies or [])}")
            logger.info(f"   IPs: {', '.join(asset.resolved_ips or [])}")
            logger.info(f"   First Seen: {asset.first_seen}")
        
        if len(assets) > 10:
            logger.info(f"\n... and {len(assets) - 10} more assets")


async def main() -> None:
    """Run the demo."""
    try:
        # Initialize database
        logger.info("Initializing database...")
        await db_manager.create_tables()
        
        # Create demo program
        program_id = await create_demo_program()
        
        # Ask user what to do
        print("\n" + "=" * 70)
        print("AutoBug Reconnaissance Pipeline Demo")
        print("=" * 70)
        print("\nOptions:")
        print("1. Run Full Reconnaissance Scan (subdomain enum + HTTP probing)")
        print("2. Run Quick Scan (HTTP probing only)")
        print("3. View Database Results")
        print("4. Exit")
        print()
        
        choice = input("Choose an option (1-4): ").strip()
        
        if choice == "1":
            await run_demo_scan(program_id)
            await view_database_results(program_id)
        elif choice == "2":
            await run_demo_quick_scan(program_id)
            await view_database_results(program_id)
        elif choice == "3":
            await view_database_results(program_id)
        elif choice == "4":
            logger.info("Exiting...")
            return
        else:
            logger.error("Invalid choice!")
            return
        
        logger.info("\n✅ Demo complete!")
        logger.info("\nNext steps:")
        logger.info("  - Add your own programs: python -m src.cli add-program")
        logger.info("  - Run scans: python -m src.cli scan full <program_id>")
        logger.info("  - Check changes: python -m src.cli scan quick <program_id>")
        
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
    except Exception as e:
        logger.exception(f"Demo failed: {e}")
        sys.exit(1)
    finally:
        await db_manager.close()


if __name__ == "__main__":
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║           AutoBug Reconnaissance Pipeline Demo            ║
    ║                                                           ║
    ║  This demo will show you how the reconnaissance          ║
    ║  pipeline works with the Diff Engine.                    ║
    ║                                                           ║
    ║  ⚠️  NOTE: Make sure scanning tools are installed!       ║
    ║  Run: python -m src.cli scan test-tools                  ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    asyncio.run(main())
