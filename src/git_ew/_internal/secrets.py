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

# Runtime secret resolution helpers.

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
        result = subprocess.run(  # noqa: S603
            shlex.split(command),
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
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
