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

from __future__ import annotations

import asyncio
import email
import imaplib
import logging
import mailbox
from datetime import date
from email import policy
from email.utils import getaddresses
from pathlib import Path
from typing import TYPE_CHECKING, Any

from git_ew._internal.email_parser import ParsedEmail, parse_email
from git_ew._internal.secrets import resolve_password

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

_logger = logging.getLogger(__name__)


class EmailFetcher:
    """Base class for email fetchers."""

    def fetch_emails(self, since: str | None = None) -> AsyncIterator[ParsedEmail]:
        """Fetch emails from the source.

        Args:
            since: Fetch emails since this date (ISO format).

        Yields:
            ParsedEmail objects.
        """
        raise NotImplementedError


class MaildirFetcher(EmailFetcher):
    """Fetch emails from a Maildir directory."""

    def __init__(self, maildir_path: str):
        """Initialize Maildir fetcher.

        Args:
            maildir_path: Path to Maildir directory.
        """
        self.maildir_path = Path(maildir_path)
        """Path to the Maildir directory."""

    async def fetch_emails(self, since: str | None = None) -> AsyncIterator[ParsedEmail]:  # noqa: ARG002
        """Fetch emails from Maildir.

        Args:
            since: Fetch emails since this date (ISO format).

        Yields:
            ParsedEmail objects.
        """
        if not self.maildir_path.exists():
            return

        # Use mailbox.Maildir to read the maildir
        mbox = mailbox.Maildir(str(self.maildir_path))
        try:
            for message in mbox:
                try:
                    raw = message.as_bytes()
                    parsed = parse_email(raw)
                    yield parsed
                except Exception as e:  # noqa: BLE001
                    # Skip malformed emails
                    _logger.debug("Skipping malformed Maildir message: %s", e)
                    continue

                # Allow event loop to process
                await asyncio.sleep(0)
        finally:
            mbox.close()


class MboxFetcher(EmailFetcher):
    """Fetch emails from an mbox file."""

    def __init__(self, mbox_path: str):
        """Initialize mbox fetcher.

        Args:
            mbox_path: Path to mbox file.
        """
        self.mbox_path = Path(mbox_path)
        """Path to the mbox file."""

    async def fetch_emails(self, since: str | None = None) -> AsyncIterator[ParsedEmail]:  # noqa: ARG002
        """Fetch emails from mbox.

        Args:
            since: Fetch emails since this date (ISO format).

        Yields:
            ParsedEmail objects.
        """
        if not self.mbox_path.exists():
            return

        mbox = mailbox.mbox(str(self.mbox_path))
        try:
            for message in mbox:
                try:
                    raw = message.as_bytes()
                    parsed = parse_email(raw)
                    yield parsed
                except Exception as e:  # noqa: BLE001
                    # Skip malformed emails
                    _logger.debug("Skipping malformed mbox message: %s", e)
                    continue

                # Allow event loop to process
                await asyncio.sleep(0)
        finally:
            mbox.close()


class IMAPFetcher(EmailFetcher):
    """Fetch emails from IMAP folders, including Fastmail accounts."""

    def __init__(
        self,
        host: str,
        username: str,
        password: str,
        *,
        port: int = 993,
        folders: list[str] | None = None,
        mailing_list: dict[str, list[str]] | None = None,
    ):
        """Initialize an IMAP fetcher."""
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.folders = folders or ["INBOX", "Sent"]
        self.mailing_list = mailing_list or {}

    async def fetch_emails(self, since: str | None = None) -> AsyncIterator[ParsedEmail]:
        """Fetch and parse messages from configured IMAP folders."""
        raw_messages = await asyncio.to_thread(self._fetch_messages, since)
        for raw_message in raw_messages:
            try:
                yield parse_email(raw_message)
            except Exception as e:  # noqa: BLE001
                _logger.debug("Skipping malformed IMAP message: %s", e)
            await asyncio.sleep(0)

    def _fetch_messages(self, since: str | None) -> list[bytes]:
        """Fetch raw messages using a synchronous IMAP connection."""
        messages: list[bytes] = []
        with imaplib.IMAP4_SSL(self.host, self.port) as client:
            client.login(self.username, self.password)
            for folder in self.folders:
                status, _ = client.select(folder, readonly=True)
                if status != "OK":
                    raise RuntimeError(f"Unable to select IMAP folder {folder!r}")

                criteria = "ALL"
                if since:
                    since_date = date.fromisoformat(since).strftime("%d-%b-%Y")
                    criteria = f"SINCE {since_date}"
                status, data = client.search(None, criteria)
                if status != "OK":
                    raise RuntimeError(f"Unable to search IMAP folder {folder!r}")

                for message_number in data[0].split():
                    if self.mailing_list:
                        status, fetched = client.fetch(message_number, "(BODY.PEEK[HEADER])")
                        if status != "OK":
                            _logger.warning("Unable to fetch headers for message %s from %s", message_number, folder)
                            continue
                        headers = b"".join(
                            item[1] for item in fetched if isinstance(item, tuple) and isinstance(item[1], bytes)
                        )
                        if not self._matches_mailing_list(headers):
                            continue

                    status, fetched = client.fetch(message_number, "(BODY.PEEK[])")
                    if status != "OK":
                        _logger.warning("Unable to fetch message %s from %s", message_number, folder)
                        continue
                    messages.extend(
                        item[1] for item in fetched if isinstance(item, tuple) and isinstance(item[1], bytes)
                    )
        return messages

    def _matches_mailing_list(self, raw_headers: bytes) -> bool:
        """Return whether headers identify a configured mailing-list message."""
        message = email.message_from_bytes(raw_headers, policy=policy.default)
        addresses = {address.lower() for address in self.mailing_list.get("addresses", [])}
        list_ids = {list_id.lower().strip("<>") for list_id in self.mailing_list.get("list_ids", [])}

        if not addresses and not list_ids:
            return True

        address_headers = (
            "To",
            "Cc",
            "Delivered-To",
            "X-Original-To",
            "Envelope-To",
            "List-Post",
        )
        header_addresses = {
            address.lower().removeprefix("mailto:")
            for header in address_headers
            for _, address in getaddresses(message.get_all(header, []))
            if address
        }
        if addresses.intersection(header_addresses):
            return True

        return any(list_id in (message.get("List-Id", "").lower().strip("<>")) for list_id in list_ids)


class PublicInboxFetcher(EmailFetcher):
    """Fetch emails from a public-inbox archive URL."""

    def __init__(self, archive_url: str):
        """Initialize public-inbox fetcher.

        Args:
            archive_url: Base URL of the public-inbox archive.
        """
        self.archive_url = archive_url.rstrip("/")
        """Base URL of the public-inbox archive."""

    def fetch_emails(self, since: str | None = None) -> AsyncIterator[ParsedEmail]:
        """Fetch emails from public-inbox archive.

        Args:
            since: Fetch emails since this date (ISO format).

        Yields:
            ParsedEmail objects.
        """
        # This would require implementing HTTP requests to fetch mbox files
        # from public-inbox archives. For now, this is a placeholder.
        # Real implementation would use httpx to fetch and parse mbox files
        raise NotImplementedError("Public-inbox fetching not yet implemented")


def get_fetcher(source_type: str, config: dict[str, Any]) -> EmailFetcher:
    """Get an email fetcher based on source type.

    Args:
        source_type: Type of source (maildir, mbox, imap, public-inbox).
        config: Configuration for the fetcher.

    Returns:
        EmailFetcher instance.

    Raises:
        ValueError: If source type is unknown.
    """
    if source_type == "maildir":
        return MaildirFetcher(config["path"])
    if source_type == "mbox":
        return MboxFetcher(config["path"])
    if source_type == "imap":
        return IMAPFetcher(
            host=config.get("host", "imap.fastmail.com"),
            port=int(config.get("port", 993)),
            username=config["username"],
            password=resolve_password(config),
            folders=config.get("folders"),
            mailing_list=config.get("mailing_list"),
        )
    if source_type == "public-inbox":
        return PublicInboxFetcher(config["url"])
    raise ValueError(f"Unknown source type: {source_type}")
