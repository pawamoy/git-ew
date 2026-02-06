"""git-ew package.

Git Email Workflow
"""

from __future__ import annotations

from git_ew._internal.cli import get_parser, main

__all__: list[str] = ["get_parser", "main"]
