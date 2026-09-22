"""Tests for email source fetchers."""

from __future__ import annotations

import mailbox
from email.message import EmailMessage
from typing import TYPE_CHECKING

import pytest

from git_ew._internal.email_fetcher import IMAPFetcher, MaildirFetcher, MboxFetcher

if TYPE_CHECKING:
    from pathlib import Path


def _email_message(message_id: str) -> EmailMessage:
    """Build a minimal message for mailbox fetcher tests."""
    message = EmailMessage()
    message["From"] = "sender@example.com"
    message["To"] = "list@example.com"
    message["Subject"] = "Test message"
    message["Message-ID"] = f"<{message_id}>"
    message.set_content("Message body")
    return message


def test_imap_fetcher_filters_by_mailing_list_headers() -> None:
    """Accept list headers and reject unrelated messages."""
    fetcher = IMAPFetcher(
        "imap.example.com",
        "user@example.com",
        "password",
        mailing_list={
            "addresses": ["zsh-workers@zsh.org"],
            "list_ids": ["zsh-workers.zsh.org"],
        },
    )

    list_headers = b"""\
Message-ID: <list@example.com>
To: zsh-workers@zsh.org
List-Id: <zsh-workers.zsh.org>

"""
    unrelated_headers = b"""\
Message-ID: <other@example.com>
To: someone@example.com

"""

    assert fetcher._matches_mailing_list(list_headers)
    assert not fetcher._matches_mailing_list(unrelated_headers)


@pytest.mark.asyncio
async def test_maildir_fetcher_reads_iterated_messages(tmp_path: Path) -> None:
    """Parse messages yielded by a Maildir iterator."""
    maildir_path = tmp_path / "maildir"
    maildir = mailbox.Maildir(maildir_path, create=True)
    maildir.add(_email_message("maildir@example.com"))
    maildir.flush()
    maildir.close()

    messages = [message async for message in MaildirFetcher(str(maildir_path)).fetch_emails()]

    assert [message.message_id for message in messages] == ["maildir@example.com"]


@pytest.mark.asyncio
async def test_mbox_fetcher_reads_iterated_messages(tmp_path: Path) -> None:
    """Parse messages yielded by an mbox iterator."""
    mbox_path = tmp_path / "messages.mbox"
    mbox = mailbox.mbox(mbox_path)
    mbox.add(_email_message("mbox@example.com"))
    mbox.flush()
    mbox.close()

    messages = [message async for message in MboxFetcher(str(mbox_path)).fetch_emails()]

    assert [message.message_id for message in messages] == ["mbox@example.com"]
