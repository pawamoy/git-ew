# Email synchronization utilities for git-ew.

from __future__ import annotations

import asyncio
import json
import logging

from git_ew._internal.database import Database
from git_ew._internal.email_fetcher import get_fetcher

_logger = logging.getLogger(__name__)


async def sync_all_sources(db: Database | None = None) -> dict[str, int | list[str]]:
    """Sync emails from all configured sources.

    Args:
        db: Database instance. If None, creates a new one.

    Returns:
        Dictionary with sync statistics.
    """
    if db is None:
        db = Database()
        await db.init_db()

    sources = await db.get_email_sources()
    stats = {
        "total_sources": len(sources),
        "processed_sources": 0,
        "total_messages": 0,
        "new_messages": 0,
        "new_threads": 0,
        "errors": [],
    }

    for source in sources:
        if not source.enabled:
            continue

        try:
            config = json.loads(source.config)
            fetcher = get_fetcher(source.source_type, config)

            source_messages = 0
            async for parsed_email in fetcher.fetch_emails():  # ty: ignore[not-iterable]
                # Check if message already exists
                existing = await db.get_message_by_id(parsed_email.message_id)
                if existing:
                    continue

                # Find or create thread
                thread_id_str = parsed_email.get_thread_id()
                thread = await db.get_thread_by_message_id(thread_id_str)

                if not thread:
                    # Create new thread
                    thread = await db.create_thread(
                        subject=parsed_email.clean_subject,
                        first_message_id=thread_id_str,
                        is_patch=parsed_email.is_patch,
                    )
                    stats["new_threads"] += 1

                # Create message
                await db.create_message(
                    message_id=parsed_email.message_id,
                    thread_id=thread.id,
                    from_email=parsed_email.from_email,
                    from_name=parsed_email.from_name,
                    subject=parsed_email.subject,
                    date=parsed_email.date,
                    body=parsed_email.body,
                    in_reply_to=parsed_email.in_reply_to,
                    is_patch=parsed_email.is_patch,
                    patch_content=parsed_email.patch_content,
                    raw_email=parsed_email.raw,
                )

                source_messages += 1
                stats["new_messages"] += 1

            stats["processed_sources"] += 1
            stats["total_messages"] += source_messages

            _logger.info(f"✓ Synced {source_messages} messages from '{source.name}'")

        except Exception as e:
            error_msg = f"Error syncing source '{source.name}': {e}"
            stats["errors"].append(error_msg)
            _logger.exception("✗ %s", error_msg)

    return stats


async def sync_command() -> int:
    """Run email sync as a standalone command."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    _logger.info("Starting email sync...")
    _logger.info("-" * 50)

    db = Database()
    await db.init_db()

    stats = await sync_all_sources(db)

    _logger.info("-" * 50)
    _logger.info("\nSync Summary:")
    _logger.info(f"  Sources processed: {stats['processed_sources']}/{stats['total_sources']}")
    _logger.info(f"  New threads: {stats['new_threads']}")
    _logger.info(f"  New messages: {stats['new_messages']}")

    if stats["errors"]:
        _logger.info(f"\n  Errors: {len(stats['errors'])}")  # ty: ignore[invalid-argument-type]
        for error in stats["errors"]:  # ty: ignore[not-iterable]
            _logger.info(f"    - {error}")

    return 0 if not stats["errors"] else 1


if __name__ == "__main__":
    import sys

    sys.exit(asyncio.run(sync_command()))
