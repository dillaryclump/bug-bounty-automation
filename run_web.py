"""
Web Application Entry Point

Run this script to start the AutoBug web dashboard and API server.

Usage:
    python run_web.py [--host HOST] [--port PORT] [--reload]

Examples:
    python run_web.py
    python run_web.py --host 0.0.0.0 --port 8080
    python run_web.py --reload  # Enable auto-reload for development
"""

import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import uvicorn
from src.config import settings


def main():
    parser = argparse.ArgumentParser(description="AutoBug Web Dashboard")
    parser.add_argument(
        "--host",
        default=settings.api_host,
        help=f"Host to bind to (default: {settings.api_host})"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=settings.api_port,
        help=f"Port to bind to (default: {settings.api_port})"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of worker processes (default: 1)"
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("🐛 AutoBug - Automated Bug Bounty Platform")
    print("=" * 60)
    print(f"Starting web server on http://{args.host}:{args.port}")
    print(f"Dashboard: http://{args.host}:{args.port}/dashboard")
    print(f"API Docs: http://{args.host}:{args.port}/api/docs")
    print("=" * 60)
    
    # Run the server
    uvicorn.run(
        "src.api.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        workers=args.workers if not args.reload else 1,
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    main()
