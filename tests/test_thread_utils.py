# SPDX-License-Identifier: ISC

# Copyright (c) 2021, Timothée Mazzucotelli and contributors

# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.

# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

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


def test_rendering_keeps_linear_replies_nested_when_flatten_is_false() -> None:
    """Keep a single reply under its parent when flattening is disabled."""
    parent = Message(
        id=1,
        message_id="parent",
        thread_id=1,
        from_email="parent@example.com",
        from_name="Parent",
        subject="Test",
        date=datetime.now(UTC),
        body="First message",
        in_reply_to=None,
    )
    reply = Message(
        id=2,
        message_id="reply",
        thread_id=1,
        from_email="reply@example.com",
        from_name="Reply",
        subject="Re: Test",
        date=datetime.now(UTC),
        body="Second message",
        in_reply_to="parent",
    )

    rendered = thread_to_nested_structure(build_thread_tree([parent, reply]), flatten=False)

    assert len(rendered) == 1
    assert rendered[0].message.message_id == "parent"
    assert len(rendered[0].children) == 1
    assert rendered[0].children[0].message.message_id == "reply"


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
