"""Runtime secret resolution helpers."""

from __future__ import annotations

import shlex
import subprocess
from typing import Any


def resolve_password(config: dict[str, Any]) -> str:
    """Resolve a password stored directly or provided by a command."""
    command = config.get("password_command")
    if command:
        result = subprocess.run(
            shlex.split(command),
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        password = result.stdout.strip()
        if not password:
            raise RuntimeError("password command returned no password")
        return password

    password = config.get("password")
    if password:
        return password
    raise RuntimeError("neither password nor password_command is configured")
