"""Runtime secret resolution helpers."""

from __future__ import annotations

import shlex
import subprocess
from typing import Any, Literal, overload


@overload
def resolve_password(config: dict[str, Any], *, required: Literal[True] = True) -> str: ...


@overload
def resolve_password(config: dict[str, Any], *, required: Literal[False]) -> str | None: ...


def resolve_password(config: dict[str, Any], *, required: bool = True) -> str | None:
    """Resolve a configured password.

    Return `None` when no password is configured and `required` is false.
    """
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
    if not required:
        return None
    raise RuntimeError("neither password nor password_command is configured")
