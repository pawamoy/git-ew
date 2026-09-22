"""Tests for Reply All metadata construction."""

from types import SimpleNamespace

from git_ew._internal.app import _reply_all_metadata


def test_reply_all_preserves_list_and_reference_chain() -> None:
    """Build recipients and references from the original message headers."""
    message = SimpleNamespace(
        message_id="reply@example.com",
        raw_email="""\
From: author@example.com
To: original-recipient@example.com
Cc: reviewer@example.com
List-Post: <mailto:zsh-workers@zsh.org>
References: <root@example.com> <parent@example.com>
Message-ID: <reply@example.com>

"""
    )

    to_email, cc, references = _reply_all_metadata(message, "root@example.com", {"contact@pawamoy.fr"})

    assert to_email == "author@example.com"
    assert cc == ["original-recipient@example.com", "reviewer@example.com", "zsh-workers@zsh.org"]
    assert references == ["root@example.com", "parent@example.com", "reply@example.com"]
