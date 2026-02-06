"""Email fetching from various sources for git-ew."""

from __future__ import annotations

import asyncio
import logging
import mailbox
from pathlib import Path
from typing import TYPE_CHECKING

from git_ew._internal.email_parser import ParsedEmail, parse_email

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


class EmailFetcher:
    """Base class for email fetchers."""

    async def fetch_emails(self, since: str | None = None) -> AsyncIterator[ParsedEmail]:
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

    async def fetch_emails(self, since: str | None = None) -> AsyncIterator[ParsedEmail]:  # noqa: ARG002  # ty: ignore[invalid-method-override]
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

        for key in mbox:
            try:
                msg = mbox.get_message(key)  # ty: ignore[invalid-argument-type]
                raw = msg.as_bytes()
                parsed = parse_email(raw)
                yield parsed
            except Exception as e:  # noqa: BLE001
                # Skip malformed emails
                logger.debug(f"Skipping malformed email {key}: {e}")
                continue

            # Allow event loop to process
            await asyncio.sleep(0)


class MboxFetcher(EmailFetcher):
    """Fetch emails from an mbox file."""

    def __init__(self, mbox_path: str):
        """Initialize mbox fetcher.

        Args:
            mbox_path: Path to mbox file.
        """
        self.mbox_path = Path(mbox_path)

    async def fetch_emails(self, since: str | None = None) -> AsyncIterator[ParsedEmail]:  # noqa: ARG002  # ty: ignore[invalid-method-override]
        """Fetch emails from mbox.

        Args:
            since: Fetch emails since this date (ISO format).

        Yields:
            ParsedEmail objects.
        """
        if not self.mbox_path.exists():
            return

        mbox = mailbox.mbox(str(self.mbox_path))

        for key in mbox:
            try:
                msg = mbox.get_message(key)  # ty: ignore[invalid-argument-type]
                raw = msg.as_bytes()
                parsed = parse_email(raw)
                yield parsed
            except Exception as e:  # noqa: BLE001
                # Skip malformed emails
                logger.debug(f"Skipping malformed email {key}: {e}")
                continue

            # Allow event loop to process
            await asyncio.sleep(0)


class PublicInboxFetcher(EmailFetcher):
    """Fetch emails from a public-inbox archive URL."""

    def __init__(self, archive_url: str):
        """Initialize public-inbox fetcher.

        Args:
            archive_url: Base URL of the public-inbox archive.
        """
        self.archive_url = archive_url.rstrip("/")

    async def fetch_emails(self, since: str | None = None) -> AsyncIterator[ParsedEmail]:
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


def get_fetcher(source_type: str, config: dict) -> EmailFetcher:
    """Get an email fetcher based on source type.

    Args:
        source_type: Type of source (maildir, mbox, public-inbox).
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
    if source_type == "public-inbox":
        return PublicInboxFetcher(config["url"])
    raise ValueError(f"Unknown source type: {source_type}")
