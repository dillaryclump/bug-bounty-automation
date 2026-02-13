"""
Main application entry point.
"""

import asyncio

from src.db.session import db_manager
from src.utils.logging import get_logger, setup_logging
from src.config import settings

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def init_database() -> None:
    """Initialize database tables."""
    logger.info("Initializing database...")
    await db_manager.create_tables()
    logger.info("✅ Database initialized successfully")


async def main() -> None:
    """Main application entry point."""
    logger.info(f"🚀 Starting {settings.app_name}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    try:
        # Initialize database
        await init_database()

        # TODO: Start FastAPI server
        # TODO: Start Prefect workflows
        # TODO: Initialize scanner fleet

        logger.info("✅ Application started successfully")
        logger.info("Ready to hunt bugs! 🐛🔍")

        # Keep running
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Shutting down...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        await db_manager.close()


if __name__ == "__main__":
    asyncio.run(main())
