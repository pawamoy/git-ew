"""Tests for thread utilities module."""

from __future__ import annotations

from datetime import UTC, datetime

from git_ew._internal.models import Message
from git_ew._internal.thread_utils import build_thread_tree


def test_build_simple_thread_tree() -> None:
    """Test building a simple linear thread."""
    messages = [
        Message(
            id=1,
            message_id="msg1",
            thread_id=1,
            from_email="user1@example.com",
            from_name="User 1",
            subject="Test",
            date=datetime.now(UTC),
            body="First message",
            in_reply_to=None,
        ),
        Message(
            id=2,
            message_id="msg2",
            thread_id=1,
            from_email="user2@example.com",
            from_name="User 2",
            subject="Re: Test",
            date=datetime.now(UTC),
            body="Reply",
            in_reply_to="msg1",
        ),
    ]

    tree = build_thread_tree(messages)

    assert len(tree) == 1
    assert tree[0].message.message_id == "msg1"
    assert len(tree[0].children) == 1
    assert tree[0].children[0].message.message_id == "msg2"


def test_build_branching_thread_tree() -> None:
    """Test building a thread with multiple branches."""
    messages = [
        Message(
            id=1,
            message_id="msg1",
            thread_id=1,
            from_email="user1@example.com",
            from_name="User 1",
            subject="Test",
            date=datetime.now(UTC),
            body="First message",
            in_reply_to=None,
        ),
        Message(
            id=2,
            message_id="msg2",
            thread_id=1,
            from_email="user2@example.com",
            from_name="User 2",
            subject="Re: Test",
            date=datetime.now(UTC),
            body="Reply 1",
            in_reply_to="msg1",
        ),
        Message(
            id=3,
            message_id="msg3",
            thread_id=1,
            from_email="user3@example.com",
            from_name="User 3",
            subject="Re: Test",
            date=datetime.now(UTC),
            body="Reply 2",
            in_reply_to="msg1",
        ),
    ]

    tree = build_thread_tree(messages)

    assert len(tree) == 1
    assert len(tree[0].children) == 2
