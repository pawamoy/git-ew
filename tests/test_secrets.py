"""Tests for runtime password resolution."""

import sys

from git_ew._internal.secrets import resolve_password


def test_resolve_direct_password() -> None:
    """Resolve a password stored directly."""
    assert resolve_password({"password": "secret"}) == "secret"


def test_resolve_password_command() -> None:
    """Resolve a password from a command's stdout."""
    command = f"{sys.executable} -c \"print('secret')\""
    assert resolve_password({"password_command": command}) == "secret"
