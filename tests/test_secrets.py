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
