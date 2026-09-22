# SPDX-License-Identifier: ISC
#
# ISC License
#
# Copyright (c) 2026, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# Why does this file exist, and why not put this in `__main__`?
#
# You might be tempted to import things from `__main__` later,
# but that will cause problems: the code will get executed twice:
#
# - When you run `python -m git_ew` python will execute
#   `__main__.py` as a script. That means there won't be any
#   `git_ew.__main__` in `sys.modules`.
# - When you import `__main__` it will get executed again (as a module) because
#   there's no `git_ew.__main__` in `sys.modules`.

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.error import URLError

import uvicorn

from git_ew._internal import debug
from git_ew._internal.config import config_command
from git_ew._internal.database import Database
from git_ew._internal.mailing_lists.zsh_workers.ingest import ingest_archives
from git_ew._internal.mailing_lists.zsh_workers.sync_archives import (
    _get_matching_archives,
    download_archive,
    fetch_archive_list,
    get_missing_archives,
)
from git_ew._internal.sync import sync_command


class _DebugInfo(argparse.Action):
    def __init__(self, nargs: int | str | None = 0, **kwargs: Any) -> None:
        super().__init__(nargs=nargs, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        print(debug._format_debug_info())
        sys.exit(0)


def _parse_archive_date(value: str, *, end_of_year: bool = False) -> date:
    """Parse a CLI archive date."""
    try:
        if len(value) == 4:
            year = int(value)
            if end_of_year:
                return date(year, 12, 31)
            return date(year, 1, 1)
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError(
            f"invalid date {value!r}; use YYYY or YYYY-MM-DD",
        ) from error


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

    # Configuration command
    subparsers.add_parser("config", help="Configure email accounts and sources")

    # Archive ingestion commands
    ingest_parser = subparsers.add_parser("ingest", help="Ingest mailing-list archives")
    ingest_subparsers = ingest_parser.add_subparsers(dest="ingest_source", required=True)
    zsh_workers_parser = ingest_subparsers.add_parser(
        "zsh-workers",
        help="Download and ingest zsh-workers archives",
    )
    zsh_workers_parser.add_argument(
        "--since",
        type=_parse_archive_date,
        help="Only include archives from this date (YYYY or YYYY-MM-DD)",
    )
    zsh_workers_parser.add_argument(
        "--until",
        type=lambda value: _parse_archive_date(value, end_of_year=True),
        help="Only include archives through this date (YYYY or YYYY-MM-DD)",
    )
    zsh_workers_parser.add_argument(
        "--archive-dir",
        type=Path,
        default=Path(".archives"),
        help="Directory for archives (default: .archives)",
    )
    zsh_workers_parser.add_argument(
        "--database",
        default="sqlite:///./git_ew.db",
        help="SQLAlchemy database URL (default: sqlite:///./git_ew.db)",
    )
    zsh_workers_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show archives to download without downloading or ingesting",
    )
    zsh_workers_parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="List archives selected for download",
    )

    return parser


def main(args: list[str] | None = None) -> int:
    """Run the main program.

    This function is executed when you type `git-ew` or `python -m git_ew`.

    Parameters:
        args: Arguments passed from the command line.

    Returns:
        An exit code.
    """
    logging.basicConfig(level=logging.INFO, format="%(message)s")
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

    if opts.command == "config":
        asyncio.run(config_command())
        return 0

    if opts.command == "ingest" and opts.ingest_source == "zsh-workers":
        opts.archive_dir.mkdir(parents=True, exist_ok=True)
        try:
            available = fetch_archive_list()
        except URLError as error:
            print(f"Error fetching zsh-workers archive list: {error}", file=sys.stderr)
            return 1

        matching = _get_matching_archives(available, opts.since, opts.until)
        missing = get_missing_archives(opts.archive_dir, available, opts.since, opts.until)
        print(f"Found {len(available)} archives available")
        print(f"Found {len(matching)} matching archives")
        print(f"Found {len(missing)} matching archives not downloaded")
        if opts.verbose:
            for filename in missing:
                print(f"  - {filename}")
        if opts.dry_run:
            print("Dry-run: no archives downloaded or ingested")
            return 0

        failed = 0
        for filename in missing:
            if not download_archive(filename, opts.archive_dir):
                failed += 1
        if failed:
            print(f"Error: {failed} archive download(s) failed", file=sys.stderr)
            return 1

        ingest_archives(opts.archive_dir, opts.database, filenames=matching)
        return 0

    # No command specified, show help
    parser.print_help()
    return 0
