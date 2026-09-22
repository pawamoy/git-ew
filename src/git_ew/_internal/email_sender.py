# Email sending functionality for git-ew.

from __future__ import annotations

import imaplib
import smtplib
from datetime import datetime
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Any

from git_ew._internal.secrets import resolve_password


class EmailSender:
    """Handle sending emails."""

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        from_email: str,
        from_name: str,
        *,
        username: str | None = None,
        password: str | None = None,
        use_tls: bool = True,
    ):
        """Initialize email sender.

        Args:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port.
            from_email: Sender email address.
            from_name: Sender name.
            username: SMTP username (if required).
            password: SMTP password (if required).
            use_tls: Whether to use TLS.
        """
        self.smtp_host = smtp_host
        """SMTP server hostname."""
        self.smtp_port = smtp_port
        """SMTP server port."""
        self.from_email = from_email
        """Sender email address."""
        self.from_name = from_name
        """Sender name."""
        self.username = username
        """SMTP username."""
        self.password = password
        """SMTP password."""
        self.use_tls = use_tls
        """Whether to use TLS."""

    def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
        references: list[str] | None = None,
        cc: list[str] | None = None,
    ) -> str:
        """Send a plain text email.

        Args:
            to_email: Recipient email address.
            subject: Email subject.
            body: Email body (plain text).
            in_reply_to: Message ID this replies to.
            references: List of message IDs in the thread.
            cc: List of CC recipients.

        Returns:
            Message ID of sent email.
        """
        msg = self.build_email(to_email, subject, body, in_reply_to, references, cc)
        self.send_message(msg)
        return msg["Message-ID"].strip("<>")

    def build_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        in_reply_to: str | None = None,
        references: list[str] | None = None,
        cc: list[str] | None = None,
    ) -> EmailMessage:
        """Build an email without sending it."""
        msg = EmailMessage()
        msg.set_content(body)

        # Set headers
        msg["From"] = f"{self.from_name} <{self.from_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg["Date"] = formatdate(localtime=True)
        msg["Message-ID"] = make_msgid(domain=self.from_email.split("@")[1])

        if cc:
            msg["Cc"] = ", ".join(cc)

        if in_reply_to:
            msg["In-Reply-To"] = f"<{in_reply_to}>"

        if references:
            msg["References"] = " ".join(f"<{ref}>" for ref in references)

        return msg

    def send_message(self, msg: EmailMessage) -> None:
        """Send a prepared email over SMTP."""
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            if self.use_tls:
                smtp.starttls()

            if self.username and self.password:
                smtp.login(self.username, self.password)

            smtp.send_message(msg)

    def send_reply(
        self,
        to_email: str,
        subject: str,
        body: str,
        in_reply_to: str,
        references: list[str] | None = None,
        cc: list[str] | None = None,
    ) -> str:
        """Send a reply email.

        Args:
            to_email: Recipient email address.
            subject: Email subject (will be prefixed with "Re:" if not present).
            body: Email body (plain text).
            in_reply_to: Message ID this replies to.
            references: List of message IDs in the thread.
            cc: List of CC recipients.

        Returns:
            Message ID of sent email.
        """
        msg = self.build_reply(to_email, subject, body, in_reply_to, references, cc)
        self.send_message(msg)
        return msg["Message-ID"].strip("<>")

    def build_reply(
        self,
        to_email: str,
        subject: str,
        body: str,
        in_reply_to: str,
        references: list[str] | None = None,
        cc: list[str] | None = None,
    ) -> EmailMessage:
        """Build a reply email without sending it."""
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        references = list(references or [])
        if in_reply_to not in references:
            references.append(in_reply_to)

        return self.build_email(
            to_email=to_email,
            subject=subject,
            body=body,
            in_reply_to=in_reply_to,
            references=references,
            cc=cc,
        )


def append_sent_message(msg: EmailMessage, config: dict[str, Any], folder: str = "Sent") -> None:
    """Append a sent message to an IMAP folder using a resolved password."""
    host = config.get("host", "imap.fastmail.com")
    port = int(config.get("port", 993))
    with imaplib.IMAP4_SSL(host, port) as client:
        client.login(config["username"], resolve_password(config))
        status, _ = client.append(
            folder,
            "\\Seen",
            imaplib.Time2Internaldate(datetime.now().timestamp()),
            msg.as_bytes(),
        )
        if status != "OK":
            raise RuntimeError(f"Unable to append sent message to IMAP folder {folder!r}")


def create_email_sender(config: dict[str, Any]) -> EmailSender:
    """Create an email sender with a resolved password."""
    return EmailSender(
        smtp_host=config.get("smtp_host", "localhost"),
        smtp_port=config.get("smtp_port", 587),
        from_email=config["from_email"],
        from_name=config.get("from_name", config["from_email"]),
        username=config.get("username"),
        password=resolve_password(config),
        use_tls=config.get("use_tls", True),
    )
