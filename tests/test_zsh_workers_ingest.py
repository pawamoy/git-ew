"""Tests for zsh-workers archive ingestion."""

from email import message_from_string

from git_ew._internal.email_parser import extract_body_and_patch


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
