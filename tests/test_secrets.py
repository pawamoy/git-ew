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

"""Tests for runtime password resolution."""

import sys

import pytest

from git_ew._internal.email_sender import create_email_sender
from git_ew._internal.secrets import resolve_password


def test_resolve_direct_password() -> None:
    """Resolve a password stored directly."""
    assert resolve_password({"password": "secret"}) == "secret"


def test_resolve_password_command() -> None:
    """Resolve a password from a command's stdout."""
    command = f"{sys.executable} -c \"print('secret')\""
    assert resolve_password({"password_command": command}) == "secret"


def test_allow_missing_optional_password() -> None:
    """Allow SMTP configurations that do not use authentication."""
    sender = create_email_sender(
        {
            "from_email": "sender@example.com",
            "from_name": "Sender",
        },
    )

    assert sender.password is None


def test_reject_missing_required_password() -> None:
    """Require a password for protocols that always authenticate."""
    with pytest.raises(RuntimeError, match="neither password nor password_command"):
        resolve_password({})
