"""Tests for email parser module."""

from __future__ import annotations

from git_ew._internal.email_parser import extract_quoted_text, parse_email


def test_parse_simple_email() -> None:
    """Test parsing a simple email."""
    raw_email = """From: John Doe <john@example.com>
To: dev@example.com
Subject: Test Subject
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test123@example.com>

This is the body of the email.
"""

    parsed = parse_email(raw_email)

    assert parsed.message_id == "test123@example.com"
    assert parsed.from_email == "john@example.com"
    assert parsed.from_name == "John Doe"
    assert parsed.subject == "Test Subject"
    assert "This is the body" in parsed.body
    assert parsed.is_patch is False


def test_parse_email_with_patch() -> None:
    """Test parsing an email with a patch."""
    raw_email = """From: Jane Dev <jane@example.com>
To: dev@example.com
Subject: [PATCH] Fix bug in parser
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <patch123@example.com>

Here's a fix for the parser bug.

diff --git a/parser.py b/parser.py
index 123..456 789
--- a/parser.py
+++ b/parser.py
@@ -10,3 +10,4 @@ def parse():
     pass
+    return True
"""

    parsed = parse_email(raw_email)

    assert parsed.message_id == "patch123@example.com"
    assert parsed.is_patch is True
    assert parsed.patch_content is not None
    assert "diff --git" in parsed.patch_content


def test_parse_reply_email() -> None:
    """Test parsing a reply email."""
    raw_email = """From: Bob Reply <bob@example.com>
To: john@example.com
Subject: Re: Test Subject
Date: Mon, 1 Jan 2024 13:00:00 +0000
Message-ID: <reply123@example.com>
In-Reply-To: <test123@example.com>
References: <test123@example.com>

I agree with this.

On Mon, 1 Jan 2024, John Doe wrote:
> This is the original message.
"""

    parsed = parse_email(raw_email)

    assert parsed.message_id == "reply123@example.com"
    assert parsed.in_reply_to == "test123@example.com"
    assert "test123@example.com" in parsed.references
    assert parsed.clean_subject == "Test Subject"


def test_extract_quoted_text() -> None:
    """Test extracting quoted text from email body."""
    body = """This is my new comment.

On Mon, 1 Jan 2024, John Doe wrote:
> This is the quoted text.
> It has multiple lines.
"""

    new_content, quoted = extract_quoted_text(body)

    assert "my new comment" in new_content
    assert "quoted text" in quoted
    assert ">" in quoted
