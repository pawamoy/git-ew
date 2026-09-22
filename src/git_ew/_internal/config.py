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

"""Interactive git-ew configuration wizard."""

from __future__ import annotations

import json
import logging
from asyncio import to_thread
from getpass import getpass
from typing import Any

from git_ew._internal.database import Database
from git_ew._internal.models import EmailSource

_logger = logging.getLogger(__name__)


def _prompt_password_config() -> dict[str, str]:
    """Prompt for direct or command-based password storage."""
    choice = input("Password storage: 1 direct, 2 command (default 1): ").strip() or "1"
    if choice == "1":
        return {"password": getpass("Password/App Password: ").strip()}
    if choice == "2":
        command = input("Password command: ").strip()
        if not command:
            raise ValueError("password command cannot be empty")
        return {"password_command": command}
    raise ValueError("password storage must be 1 or 2")


def _prompt_email_config() -> dict[str, Any]:
    """Collect email delivery settings from the terminal."""
    _logger.info("Email Configuration (for sending replies)")
    _logger.info("-" * 50)
    smtp_host = input("SMTP Host (e.g., smtp.fastmail.com): ").strip()
    smtp_port = input("SMTP Port (default 587): ").strip() or "587"
    from_email = input("Your Email Address: ").strip()
    from_name = input("Your Name: ").strip()
    username = input("SMTP Username (default: same as email): ").strip() or from_email
    use_tls = input("Use TLS? (Y/n): ").strip().lower() != "n"

    email_config: dict[str, Any] = {
        "smtp_host": smtp_host,
        "smtp_port": int(smtp_port),
        "from_email": from_email,
        "from_name": from_name,
        "username": username,
        "use_tls": use_tls,
        **_prompt_password_config(),
    }
    return email_config


def _prompt_email_source() -> EmailSource | None:
    """Collect an email source from the terminal."""
    _logger.info("Email Source Configuration")
    _logger.info("-" * 50)
    _logger.info("Where should git-ew fetch emails from?")
    _logger.info("1. Maildir (local maildir folder)")
    _logger.info("2. Mbox (mbox archive file)")
    _logger.info("3. IMAP (Fastmail or another IMAP server)")
    _logger.info("4. Skip for now")

    choice = input("\nChoice (1-4): ").strip()
    if choice == "1":
        source = EmailSource(
            name=input("Source name (e.g., 'my-maildir'): ").strip(),
            source_type="maildir",
            config=json.dumps({"path": input("Path to maildir folder: ").strip()}),
            enabled=True,
        )
    elif choice == "2":
        source = EmailSource(
            name=input("Source name (e.g., 'mailing-list'): ").strip(),
            source_type="mbox",
            config=json.dumps({"path": input("Path to mbox file: ").strip()}),
            enabled=True,
        )
    elif choice == "3":
        folders = input("Folders (comma-separated, default: INBOX,Sent): ").strip() or "INBOX,Sent"
        addresses = input("Mailing-list addresses (default: zsh-workers@zsh.org): ").strip() or "zsh-workers@zsh.org"
        list_ids = (
            input("Mailing-list List-Id values (default: zsh-workers.zsh.org): ").strip() or "zsh-workers.zsh.org"
        )
        source = EmailSource(
            name=input("Source name (e.g., 'fastmail'): ").strip(),
            source_type="imap",
            config=json.dumps(
                {
                    "host": input("IMAP Host (default: imap.fastmail.com): ").strip() or "imap.fastmail.com",
                    "port": int(input("IMAP Port (default: 993): ").strip() or "993"),
                    "username": input("IMAP Username (your Fastmail address): ").strip(),
                    "folders": [folder.strip() for folder in folders.split(",") if folder.strip()],
                    "mailing_list": {
                        "addresses": [address.strip().lower() for address in addresses.split(",") if address.strip()],
                        "list_ids": [list_id.strip().lower() for list_id in list_ids.split(",") if list_id.strip()],
                    },
                    **_prompt_password_config(),
                },
            ),
            enabled=True,
        )
    else:
        _logger.info("Skipped email source configuration")
        return None

    return source


async def config_command() -> None:
    """Configure email delivery and ingestion sources interactively."""
    _logger.info("=== git-ew Configuration Wizard ===")

    db = Database()
    _logger.info("Initializing database")
    await db.init_db()
    _logger.info("Database initialized")

    email_config = await to_thread(_prompt_email_config)
    await db.set_config("email_config", email_config)
    _logger.info("Email configuration saved")

    source = await to_thread(_prompt_email_source)
    if source is None:
        return

    async with db.session() as session:
        session.add(source)
    _logger.info("Email source added")
    _logger.info("=" * 50)
    _logger.info("Configuration complete")
