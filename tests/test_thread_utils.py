"""Tests for thread utilities module."""

from __future__ import annotations

from datetime import UTC, datetime

from git_ew._internal.models import Message
from git_ew._internal.thread_utils import build_thread_tree, thread_to_nested_structure


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


def test_rendering_splits_quotes_without_mutating_message() -> None:
    """Keep stored message bodies unchanged while preparing the thread view."""
    original_body = "New reply\n\n> Earlier message"
    message = Message(
        id=1,
        message_id="msg1",
        thread_id=1,
        from_email="user@example.com",
        from_name="User",
        subject="Test",
        date=datetime.now(UTC),
        body=original_body,
        in_reply_to=None,
    )

    rendered = thread_to_nested_structure(build_thread_tree([message]))

    assert message.body == original_body
    assert rendered[0].body == "New reply"
    assert rendered[0].quoted_body == "> Earlier message"
