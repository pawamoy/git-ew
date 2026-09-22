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

"""Tests for Reply All metadata construction."""

from dataclasses import dataclass

from git_ew._internal.app import _reply_all_metadata


@dataclass
class _ReplyMessage:
    """Store the message fields used to build reply metadata."""

    message_id: str
    raw_email: str


def test_reply_all_preserves_list_and_reference_chain() -> None:
    """Build recipients and references from the original message headers."""
    message = _ReplyMessage(
        message_id="reply@example.com",
        raw_email="""\
From: author@example.com
To: original-recipient@example.com
Cc: reviewer@example.com
List-Post: <mailto:zsh-workers@zsh.org>
References: <root@example.com> <parent@example.com>
Message-ID: <reply@example.com>

""",
    )

    to_email, cc, references = _reply_all_metadata(message, "root@example.com", {"contact@pawamoy.fr"})

    assert to_email == "author@example.com"
    assert cc == ["original-recipient@example.com", "reviewer@example.com", "zsh-workers@zsh.org"]
    assert references == ["root@example.com", "parent@example.com", "reply@example.com"]
