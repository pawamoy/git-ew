"""Archive ingestion module for zsh-workers mailing list archives."""

import email
import logging
import tarfile
import tempfile
from datetime import datetime
from email.header import decode_header
from email.message import Message as EmailMessage
from pathlib import Path
from typing import Iterator

from git_ew._internal.database import Database
from git_ew._internal.models import Message, Thread

logger = logging.getLogger(__name__)


def decode_email_header(header_value: str) -> str:
    """Decode RFC 2047 encoded-word headers to plain text.

    Args:
        header_value: Raw header value (may contain encoded-words like =?UTF-8?Q?...?=).

    Returns:
        Decoded string.
    """
    if not header_value:
        return ""

    try:
        # decode_header returns a list of tuples: (decoded_bytes, charset)
        decoded_parts = []
        for decoded_bytes, charset in decode_header(header_value):
            if isinstance(decoded_bytes, bytes):
                # If we got bytes, decode with the specified charset (or utf-8 as fallback)
                try:
                    decoded_str = decoded_bytes.decode(charset or "utf-8", errors="replace")
                except (TypeError, LookupError):
                    decoded_str = decoded_bytes.decode("utf-8", errors="replace")
            else:
                # Already a string
                decoded_str = decoded_bytes or ""
            decoded_parts.append(decoded_str)
        return "".join(decoded_parts)
    except Exception:
        # Fallback: return original if decoding fails
        return header_value


def parse_email_address(from_header: str) -> tuple[str, str]:
    """Parse From header to extract name and email address.

    Args:
        from_header: Raw From header value (may be "Name <email@example.com>" or just "email@example.com").

    Returns:
        Tuple of (name, email).
    """
    from email.utils import parseaddr

    # parseaddr handles both "Name <email>" and "email" formats
    name, email = parseaddr(from_header)

    # Decode the name if it contains encoded-words
    if name:
        name = decode_email_header(name)

    # If name is empty, use email as name
    if not name:
        name = email or from_header

    return name, email


def extract_emails_from_archive(archive_path: Path) -> Iterator[tuple[str, EmailMessage]]:
    """Extract email files from a .tgz archive.

    Args:
        archive_path: Path to the .tgz archive file.

    Yields:
        Tuples of (filename, email_message) for each email found.
    """
    with tarfile.open(archive_path, "r:gz") as tar:
        for member in tar.getmembers():
            if member.isfile() and not member.name.startswith("."):
                # Extract to temporary location and read
                f = tar.extractfile(member)
                if f:
                    try:
                        content = f.read()
                        msg = email.message_from_bytes(content)
                        yield (member.name, msg)
                    except Exception:
                        # Skip files that can't be parsed as emails
                        pass


def get_email_message_id(msg: EmailMessage) -> str | None:
    """Extract message ID from email header.

    Args:
        msg: Email message object.

    Returns:
        Message ID or None if not found.
    """
    msg_id = msg.get("Message-ID")
    if msg_id:
        # Clean up message ID (remove angle brackets if present)
        return msg_id.strip("<>")
    return None


def get_email_in_reply_to(msg: EmailMessage) -> str | None:
    """Extract In-Reply-To from email header.

    Args:
        msg: Email message object.

    Returns:
        In-Reply-To ID or None if not found.
    """
    in_reply_to = msg.get("In-Reply-To")
    if in_reply_to:
        return in_reply_to.strip("<>")
    return None


def get_email_references(msg: EmailMessage) -> list[str]:
    """Extract References from email header.

    Args:
        msg: Email message object.

    Returns:
        List of reference message IDs.
    """
    refs = msg.get("References")
    if refs:
        # References are space-separated message IDs
        return [ref.strip("<>") for ref in refs.split() if ref.strip()]
    return []


def get_email_xseq(msg: EmailMessage) -> int | None:
    """Extract X-seq number from email header.

    The X-seq header contains the sequence number in the mailing list format:
    "zsh-workers 44316" means message #44316.

    Args:
        msg: Email message object.

    Returns:
        Sequence number or None if not found.
    """
    xseq = msg.get("X-seq")
    if xseq:
        # Format is typically "zsh-workers 44316"
        parts = xseq.strip().split()
        if len(parts) >= 2:
            try:
                return int(parts[-1])  # Last part should be the number
            except ValueError:
                pass
    return None


def find_email_by_xseq(
    archive_dir: Path,
    xseq_number: int,
) -> tuple[EmailMessage, int] | None:
    """Find an email by its X-seq number by searching through archives.

    Args:
        archive_dir: Directory containing .tgz archives.
        xseq_number: The X-seq number to search for (e.g., 44316 for msg00353).

    Returns:
        Tuple of (email_message, xseq_number) if found, None otherwise.
    """
    for archive_path in sorted(archive_dir.glob("*.tgz")):
        try:
            for filename, msg in extract_emails_from_archive(archive_path):
                xseq = get_email_xseq(msg)
                if xseq == xseq_number:
                    return (msg, xseq)
        except Exception:
            # Skip archives that can't be read
            continue
    return None


def ingest_archive(
    archive_path: Path,
    db: Database,
    on_email_found: callable = None,
) -> tuple[int, int]:
    """Ingest emails from an archive into the database.

    Args:
        archive_path: Path to the .tgz archive.
        db: Database instance.
        on_email_found: Optional callback function called when an email is found.
                       Called with (filename, msg, message_id).

    Returns:
        Tuple of (inserted_count, skipped_count) for newly inserted vs existing emails.
    """
    inserted = 0
    skipped = 0

    with db.session_maker() as session:
        for filename, msg in extract_emails_from_archive(archive_path):
            message_id = get_email_message_id(msg)
            if not message_id:
                continue

            # Callback for finding specific emails
            if on_email_found:
                on_email_found(filename, msg, message_id)

            # Check if message already exists (deduplication)
            existing = session.query(Message).filter_by(message_id=message_id).first()
            if existing:
                skipped += 1
                continue

            # Parse email metadata
            from_header = msg.get("From", "unknown@example.com")
            from_name, from_email = parse_email_address(from_header)
            subject = decode_email_header(msg.get("Subject", "(no subject)"))
            date_str = msg.get("Date", "")
            in_reply_to = get_email_in_reply_to(msg)

            # Parse date
            try:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except (TypeError, ValueError):
                date = datetime.now()

            # Get email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        payload = part.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            # Get charset from Content-Type header, default to utf-8
                            charset = part.get_content_charset() or "utf-8"
                            try:
                                body = payload.decode(charset, errors="replace")
                            except (TypeError, LookupError):
                                # Unknown charset, try utf-8 as fallback
                                body = payload.decode("utf-8", errors="replace")
                        else:
                            body = payload
                        break
            else:
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    # Get charset from Content-Type header, default to utf-8
                    charset = msg.get_content_charset() or "utf-8"
                    try:
                        body = payload.decode(charset, errors="replace")
                    except (TypeError, LookupError):
                        # Unknown charset, try utf-8 as fallback
                        body = payload.decode("utf-8", errors="replace")
                else:
                    body = msg.get_payload()

            # Try to find or create thread
            # Use the first message in References (original message) as thread root
            # Fall back to in_reply_to, then to message_id if neither exist
            references = get_email_references(msg)
            intended_thread_root = None
            if references:
                # The first message in the References chain is the original message
                intended_thread_root = references[0]
                thread_root_id = references[0]
            elif in_reply_to:
                # If no References, use in_reply_to
                intended_thread_root = in_reply_to
                thread_root_id = in_reply_to
            else:
                # If neither References nor in_reply_to, this is the start of a new thread
                thread_root_id = message_id

            # Check if we already have a thread for this root
            thread = session.query(Thread).filter_by(first_message_id=thread_root_id).first()

            if not thread:
                # Check if the intended thread root message exists in our database
                if intended_thread_root and intended_thread_root != message_id:
                    root_message = session.query(Message).filter_by(message_id=intended_thread_root).first()
                    if root_message:
                        # Found the root message, use its thread instead
                        thread = session.query(Thread).filter_by(id=root_message.thread_id).first()
                    else:
                        # We don't have the actual first message, check if we have the in_reply_to message
                        # and if so, use its thread
                        if in_reply_to:
                            in_reply_message = session.query(Message).filter_by(message_id=in_reply_to).first()
                            if in_reply_message:
                                thread = session.query(Thread).filter_by(id=in_reply_message.thread_id).first()

                        if not thread:
                            # Still no thread, log a warning and create a new thread
                            logger.warning(
                                f"Thread first message not available: {intended_thread_root}. "
                                f"Using earliest available message {message_id} ({date}) as thread root instead."
                            )
                            thread_root_id = message_id

                if not thread:
                    # Create new thread
                    thread = Thread(
                        subject=subject,
                        first_message_id=thread_root_id,
                    created_at=date,
                    updated_at=date,
                    is_patch="patch" in subject.lower(),
                    status="open",
                )
                session.add(thread)
                session.flush()  # Ensure thread has an ID
            else:
                # Thread already exists, update its updated_at to the latest message date
                # Handle timezone-aware and naive datetimes safely
                try:
                    if date > thread.updated_at:
                        thread.updated_at = date
                except TypeError:
                    # Can't compare aware and naive datetimes, skip the update
                    pass

            # Create message record
            message = Message(
                message_id=message_id,
                in_reply_to=in_reply_to,
                thread_id=thread.id,
                from_email=from_email,
                from_name=from_name,
                subject=subject,
                date=date,
                body=body,
                raw_email=str(msg),
                is_patch="patch" in subject.lower() or "---" in body[:500],
            )
            session.add(message)
            inserted += 1

        session.commit()

    return inserted, skipped
