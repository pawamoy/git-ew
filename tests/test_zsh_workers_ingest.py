"""Tests for zsh-workers archive ingestion."""

from email import message_from_string
from types import SimpleNamespace
from typing import TYPE_CHECKING

import pytest

from git_ew._internal.email_parser import extract_body_and_patch
from git_ew._internal.mailing_lists.zsh_workers import ingest

if TYPE_CHECKING:
    from pathlib import Path


def test_extract_mime_patch_attachment() -> None:
    """Extract a patch attachment separately from the message body."""
    msg = message_from_string(
        """\
From: sender@example.com
Subject: A patch
Content-Type: multipart/mixed; boundary="boundary"

--boundary
Content-Type: text/plain; charset="utf-8"

Please review this change.
--boundary
Content-Type: text/x-patch; name="change.patch"
Content-Disposition: attachment; filename="change.patch"

diff --git a/file b/file
--- a/file
+++ b/file
@@ -1 +1 @@
-old
+new
--boundary--
""",
    )

    body, patch_content = extract_body_and_patch(msg)

    assert body == "Please review this change."
    assert patch_content is not None
    assert "diff --git a/file b/file" in patch_content


def test_ingest_archives_uses_selected_filenames(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Ignore local archives outside the selected date range."""
    (tmp_path / "selected.tgz").touch()
    (tmp_path / "outside-range.tgz").touch()
    ingested: list[str] = []

    fake_metadata = SimpleNamespace(create_all=lambda _engine: None)
    monkeypatch.setattr(ingest, "Base", SimpleNamespace(metadata=fake_metadata))
    monkeypatch.setattr(ingest, "create_engine", lambda _url: object())
    monkeypatch.setattr(ingest, "sessionmaker", lambda **_kwargs: object())

    def record_archive(archive_path: Path, _db: object) -> tuple[int, int]:
        ingested.append(archive_path.name)
        return 1, 0

    monkeypatch.setattr(ingest, "ingest_archive", record_archive)

    inserted, skipped = ingest.ingest_archives(
        tmp_path,
        filenames=["selected.tgz"],
        verbose=False,
    )

    assert (inserted, skipped) == (1, 0)
    assert ingested == ["selected.tgz"]
