"""Command-line interface module for git-ew."""

from __future__ import annotations

import argparse
import asyncio
import sys
from typing import Any

import uvicorn

from git_ew._internal import debug
from git_ew._internal.database import Database
from git_ew._internal.sync import sync_command


class _DebugInfo(argparse.Action):
    def __init__(self, nargs: int | str | None = 0, **kwargs: Any) -> None:
        super().__init__(nargs=nargs, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        debug._print_debug_info()
        sys.exit(0)


def get_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser.

    Returns:
        An argparse parser.
    """
    parser = argparse.ArgumentParser(
        prog="git-ew",
        description="Git Email Workflow - A web interface for email-based git workflows",
    )
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {debug._get_version()}")
    parser.add_argument("--debug-info", action=_DebugInfo, help="Print debug information.")

    # Subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Server command
    server_parser = subparsers.add_parser("serve", help="Start the web server")
    server_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    server_parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port to bind to (default: 8000)",
    )
    server_parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload for development",
    )

    # Init command
    subparsers.add_parser("init", help="Initialize the database")

    # Sync command
    subparsers.add_parser("sync", help="Sync emails from configured sources")

    return parser


def main(args: list[str] | None = None) -> int:
    """Run the main program.

    This function is executed when you type `git-ew` or `python -m git_ew`.

    Parameters:
        args: Arguments passed from the command line.

    Returns:
        An exit code.
    """
    parser = get_parser()
    opts = parser.parse_args(args=args)

    if opts.command == "serve":
        # Start the web server
        print(f"Starting git-ew server at http://{opts.host}:{opts.port}")
        print("Press Ctrl+C to stop the server")

        uvicorn.run(
            "git_ew._internal.app:app",
            host=opts.host,
            port=opts.port,
            reload=opts.reload,
        )
        return 0

    if opts.command == "init":
        # Initialize the database
        async def init_database() -> None:
            db = Database()
            await db.init_db()
            print("Database initialized successfully")

        asyncio.run(init_database())
        return 0

    if opts.command == "sync":
        # Sync emails from sources
        return asyncio.run(sync_command())

    # No command specified, show help
    parser.print_help()
    return 0
