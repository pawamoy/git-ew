"""Email parsing utilities for git-ew."""

from __future__ import annotations

import email
import re
from datetime import UTC, datetime
from email import policy
from email.utils import parseaddr, parsedate_to_datetime


class ParsedEmail:
    """Represents a parsed email message."""

    def __init__(
        self,
        message_id: str,
        from_email: str,
        from_name: str,
        subject: str,
        date: datetime,
        body: str,
        *,
        in_reply_to: str | None = None,
        references: list[str] | None = None,
        is_patch: bool = False,
        patch_content: str | None = None,
        raw: str | None = None,
    ):
        """Initialize parsed email.

        Args:
            message_id: Unique message ID.
            from_email: Sender email address.
            from_name: Sender name.
            subject: Email subject.
            date: Email date.
            body: Email body text.
            in_reply_to: Message ID this replies to.
            references: List of referenced message IDs.
            is_patch: Whether this email contains a patch.
            patch_content: Extracted patch content.
            raw: Raw email content.
        """
        self.message_id = message_id
        self.from_email = from_email
        self.from_name = from_name
        self.subject = subject
        self.date = date
        self.body = body
        self.in_reply_to = in_reply_to
        self.references = references or []
        self.is_patch = is_patch
        self.patch_content = patch_content
        self.raw = raw

    def get_thread_id(self) -> str:
        """Get the thread ID (first message in chain).

        Returns:
            Thread ID (the first message ID in the references chain).
        """
        if self.references:
            return self.references[0]
        if self.in_reply_to:
            return self.in_reply_to
        return self.message_id

    @property
    def clean_subject(self) -> str:
        """Get subject with RE: and similar prefixes removed.

        Returns:
            Clean subject.
        """
        subject = self.subject
        # Remove RE:, Re:, FWD:, Fwd: etc.
        subject = re.sub(r"^(RE|Re|FW|Fw|FWD|Fwd):\s*", "", subject, flags=re.IGNORECASE)
        subject = re.sub(r"^\[.*?\]\s*", "", subject)  # Remove [tag] prefixes
        return subject.strip()


def parse_email(raw_email: str | bytes) -> ParsedEmail:
    """Parse a raw email message.

    Args:
        raw_email: Raw email content as string or bytes.

    Returns:
        ParsedEmail object.
    """
    raw_email_bytes = raw_email.encode("utf-8") if isinstance(raw_email, str) else raw_email

    msg = email.message_from_bytes(raw_email_bytes, policy=policy.default)

    # Extract basic headers
    message_id = msg.get("Message-ID", "").strip("<>")
    subject = msg.get("Subject", "No Subject")

    # Parse from address
    from_header = msg.get("From", "")
    from_name, from_email = parseaddr(from_header)
    if not from_name:
        from_name = from_email

    # Parse date
    date_header = msg.get("Date")
    try:
        date = parsedate_to_datetime(date_header) if date_header else datetime.now(UTC)
    except Exception:  # noqa: BLE001
        date = datetime.now(UTC)

    # Get reply information
    in_reply_to = msg.get("In-Reply-To", "").strip("<>") or None
    references_header = msg.get("References", "")
    references = [ref.strip("<>") for ref in references_header.split() if ref.strip("<>")]

    # Extract body
    body = ""
    patch_content = None
    is_patch = False

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            if content_type == "text/plain":
                try:
                    body = part.get_content()
                    break
                except Exception:  # noqa: BLE001, S112
                    continue
    else:
        try:
            body = msg.get_content()
        except Exception:  # noqa: BLE001
            body = ""

    # Detect and extract patches
    # Look for git diff format or unified diff format
    patch_patterns = [
        r"diff --git",
        r"^---.*\n\+\+\+",
        r"^Index:",
    ]

    for pattern in patch_patterns:
        if re.search(pattern, body, re.MULTILINE):
            is_patch = True
            # Extract everything from the first diff marker
            match = re.search(r"(diff --git.*|^---.*\n\+\+\+.*|^Index:.*)", body, re.MULTILINE | re.DOTALL)
            if match:
                patch_content = body[match.start() :]
            break

    # Also check for [PATCH] in subject
    if "[PATCH]" in subject.upper() or "PATCH" in subject.upper():
        is_patch = True

    return ParsedEmail(
        message_id=message_id,
        from_email=from_email,
        from_name=from_name,
        subject=subject,
        date=date,
        body=body,
        in_reply_to=in_reply_to,
        references=references,
        is_patch=is_patch,
        patch_content=patch_content,
        raw=raw_email_bytes.decode("utf-8", errors="replace"),
    )


def extract_quoted_text(body: str) -> tuple[str, str]:
    """Separate new content from quoted text.

    Args:
        body: Email body.

    Returns:
        Tuple of (new_content, quoted_content).
    """
    lines = body.split("\n")
    new_lines = []
    quoted_lines = []
    in_quote = False

    for line in lines:
        stripped = line.strip()
        # Common quote indicators
        if stripped.startswith((">", "|")):
            in_quote = True
            quoted_lines.append(line)
        elif stripped.startswith("On ") and " wrote:" in line:
            # "On [date] [person] wrote:" pattern
            in_quote = True
            quoted_lines.append(line)
        elif in_quote:
            quoted_lines.append(line)
        else:
            new_lines.append(line)

    return "\n".join(new_lines).strip(), "\n".join(quoted_lines).strip()


def normalize_message_id(message_id: str) -> str:
    """Normalize a message ID by removing angle brackets.

    Args:
        message_id: Message ID.

    Returns:
        Normalized message ID.
    """
    return message_id.strip("<>")
