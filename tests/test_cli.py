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

"""Tests for the CLI."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import pytest

from git_ew import main
from git_ew._internal import cli, debug

if TYPE_CHECKING:
    from pathlib import Path


def test_main() -> None:
    """Basic CLI test."""
    assert main([]) == 0


def test_show_help(capsys: pytest.CaptureFixture) -> None:
    """Show help.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    with pytest.raises(SystemExit):
        main(["-h"])
    captured = capsys.readouterr()
    assert "git-ew" in captured.out


def test_show_version(capsys: pytest.CaptureFixture) -> None:
    """Show version.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    with pytest.raises(SystemExit):
        main(["-V"])
    captured = capsys.readouterr()
    assert debug._get_version() in captured.out


def test_show_debug_info(capsys: pytest.CaptureFixture) -> None:
    """Show debug information.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    with pytest.raises(SystemExit):
        main(["--debug-info"])
    captured = capsys.readouterr().out.lower()
    assert "python" in captured
    assert "system" in captured
    assert "environment" in captured
    assert "packages" in captured


def test_archive_year_until_includes_end_of_year() -> None:
    """Interpret a year-only upper bound as the end of that year."""
    assert cli._parse_archive_date("2026", end_of_year=True) == date(2026, 12, 31)


def test_archive_filters_apply_to_ingestion(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Pass only date-matching archives to the ingestion step."""
    available = {
        "before.tgz": date(2023, 12, 31),
        "matching.tgz": date(2024, 6, 1),
        "after.tgz": date(2025, 1, 1),
    }
    ingested_filenames: list[str] = []

    monkeypatch.setattr(cli, "fetch_archive_list", lambda: available)
    monkeypatch.setattr(cli, "download_archive", lambda _filename, _archive_dir: True)

    def record_ingestion(
        _archive_dir: Path,
        _database_url: str,
        *,
        filenames: list[str],
    ) -> tuple[int, int]:
        ingested_filenames.extend(filenames)
        return 0, 0

    monkeypatch.setattr(cli, "ingest_archives", record_ingestion)

    result = main(
        [
            "ingest",
            "zsh-workers",
            "--since",
            "2024-01-01",
            "--until",
            "2024-12-31",
            "--archive-dir",
            str(tmp_path),
        ],
    )

    assert result == 0
    assert ingested_filenames == ["matching.tgz"]
