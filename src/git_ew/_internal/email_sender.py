# Email sending functionality for git-ew.

from __future__ import annotations

import smtplib
from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from typing import Any


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

        # Send email
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
            if self.use_tls:
                smtp.starttls()

            if self.username and self.password:
                smtp.login(self.username, self.password)

            smtp.send_message(msg)

        return msg["Message-ID"].strip("<>")

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
        # Add Re: prefix if not present
        if not subject.lower().startswith("re:"):
            subject = f"Re: {subject}"

        # Build references list
        if references is None:
            references = []

        # Add in_reply_to to references if not already there
        if in_reply_to not in references:
            references.append(in_reply_to)

        return self.send_email(
            to_email=to_email,
            subject=subject,
            body=body,
            in_reply_to=in_reply_to,
            references=references,
            cc=cc,
        )


def create_email_sender(config: dict[str, Any]) -> EmailSender:
    """Create an email sender from configuration.

    Args:
        config: Configuration dictionary with SMTP settings.

    Returns:
        EmailSender instance.
    """
    return EmailSender(
        smtp_host=config.get("smtp_host", "localhost"),
        smtp_port=config.get("smtp_port", 587),
        from_email=config["from_email"],
        from_name=config.get("from_name", config["from_email"]),
        username=config.get("username"),
        password=config.get("password"),
        use_tls=config.get("use_tls", True),
    )
