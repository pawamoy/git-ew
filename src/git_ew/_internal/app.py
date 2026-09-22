# FastAPI web application for git-ew.

from __future__ import annotations

import asyncio
import email
import imaplib
import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from email import policy
from email.utils import getaddresses
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from git_ew._internal.database import Database
from git_ew._internal.email_sender import append_sent_message, create_email_sender
from git_ew._internal.sync import sync_all_sources
from git_ew._internal.thread_utils import build_thread_tree, thread_to_nested_structure

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class _ReplySource(Protocol):
    """Provide the message fields needed to prepare a reply."""

    @property
    def message_id(self) -> str: ...

    @property
    def raw_email(self) -> str | None: ...

# Global database instance
db: Database | None = None
"""Global database instance."""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Application lifespan manager."""
    global db  # noqa: PLW0603
    db = Database()
    await db.init_db()
    yield
    # Cleanup if needed


app = FastAPI(title="git-ew", description="Git Email Workflow", lifespan=lifespan)
"""FastAPI application instance."""

# Setup templates
template_dir = Path(__file__).parent.parent / "templates"
"""Path to templates directory."""
template_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(template_dir))
"""Jinja2 templates renderer."""

# Setup static files
static_dir = Path(__file__).parent.parent / "static"
"""Path to static files directory."""
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Pydantic models for API
class CommentCreate(BaseModel):
    """Model for creating a comment."""

    body: str
    """Comment body text."""
    in_reply_to: str | None = None
    """Message ID this comment is replying to."""


class ThreadUpdate(BaseModel):
    """Model for updating a thread."""

    status: str | None = None
    """New status for the thread (open or closed)."""


def _reply_all_metadata(
    message: _ReplySource,
    thread_root_id: str,
    own_addresses: set[str],
) -> tuple[str, list[str], list[str]]:
    """Build Reply All recipients and references from a stored message."""
    raw_email = message.raw_email or ""
    parsed = email.message_from_string(raw_email, policy=policy.default)

    def addresses(*headers: str) -> list[str]:
        values = [
            value.replace("<mailto:", "<").replace("mailto:", "")
            for header in headers
            for value in parsed.get_all(header, [])
        ]
        return [address.lower() for _, address in getaddresses(values) if address]

    reply_targets = addresses("Reply-To") or addresses("From")
    original_recipients = addresses("To", "Cc", "List-Post")
    candidates = list(dict.fromkeys(reply_targets + original_recipients))
    candidates = [address for address in candidates if address not in own_addresses]
    if not candidates:
        raise ValueError("No external recipients found for reply")

    to_email = candidates[0]
    cc = candidates[1:]
    references = [
        reference.strip("<>")
        for header in parsed.get_all("References", [])
        for reference in header.split()
        if reference.strip("<>")
    ]
    message_id = message.message_id
    if not references:
        references.append(thread_root_id)
    if message_id not in references:
        references.append(message_id)
    return to_email, cc, references


# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    """Show all email threads."""
    assert db is not None  # noqa: S101
    threads = await db.get_threads()
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "threads": threads,
        },
    )


@app.get("/thread/{thread_id}", response_class=HTMLResponse)
async def view_thread(request: Request, thread_id: int, *, flatten: bool = True) -> HTMLResponse:
    """View a specific thread with all messages.

    Args:
        request: FastAPI request.
        thread_id: Thread ID.
        flatten: Whether to flatten linear chains.

    Returns:
        HTML response.
    """
    assert db is not None  # noqa: S101
    thread = await db.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Build thread tree
    tree = build_thread_tree(thread.messages)
    nested_messages = thread_to_nested_structure(tree)

    return templates.TemplateResponse(
        request,
        "thread.html",
        {
            "thread": thread,
            "messages": nested_messages,
        },
    )


@app.post("/api/thread/{thread_id}/comment")
async def post_comment(thread_id: int, comment: CommentCreate) -> JSONResponse:
    """Post a comment to a thread (sends an email).

    Args:
        thread_id: Thread ID.
        comment: Comment data.

    Returns:
        JSON response with created message.
    """
    assert db is not None  # noqa: S101
    thread = await db.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    # Get email configuration
    email_config = await db.get_config("email_config")
    if not email_config:
        raise HTTPException(status_code=400, detail="Email not configured")

    # Create email sender
    sender = create_email_sender(email_config)

    own_addresses = {
        address.lower() for address in (email_config.get("from_email"), email_config.get("username")) if address
    }

    # Determine Reply All recipients and references.
    if comment.in_reply_to:
        # Get the message we're replying to
        reply_to_msg = await db.get_message_by_id(comment.in_reply_to)
        if not reply_to_msg:
            raise HTTPException(status_code=404, detail="Reply-to message not found")

        source_message = reply_to_msg
        subject = reply_to_msg.subject
    else:
        # Reply to the first message in the thread
        first_msg = next((m for m in thread.messages if m.message_id == thread.first_message_id), None)
        if not first_msg:
            raise HTTPException(status_code=404, detail="First message not found")

        source_message = first_msg
        subject = thread.subject

    try:
        to_email, cc, references = _reply_all_metadata(source_message, thread.first_message_id, own_addresses)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    # Build and send the email.
    outgoing = sender.build_reply(
        to_email=to_email,
        subject=subject,
        body=comment.body,
        in_reply_to=comment.in_reply_to or thread.first_message_id,
        references=references,
        cc=cc,
    )
    try:
        sender.send_message(outgoing)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}") from e

    # Store in database
    message_id = outgoing["Message-ID"].strip("<>")
    message = await db.create_message(
        message_id=message_id,
        thread_id=thread_id,
        from_email=email_config["from_email"],
        from_name=email_config.get("from_name", email_config["from_email"]),
        subject=outgoing["Subject"],
        date=datetime.now(UTC),
        body=comment.body,
        in_reply_to=comment.in_reply_to or thread.first_message_id,
        raw_email=outgoing.as_string(),
    )

    sent_folder_saved = False
    sent_folder_error = "No IMAP source configured"
    for source in await db.get_email_sources():
        if not source.enabled or source.source_type != "imap":
            continue
        imap_config = json.loads(source.config)
        folders = imap_config.get("folders", [])
        sent_folder = next((folder for folder in folders if folder.lower() == "sent"), "Sent")
        try:
            await asyncio.to_thread(append_sent_message, outgoing, imap_config, sent_folder)
            sent_folder_saved = True
            sent_folder_error = ""
        except (imaplib.IMAP4.error, OSError, RuntimeError) as error:
            sent_folder_error = str(error)
        break

    return JSONResponse(
        content={
            "message_id": message.message_id,
            "success": True,
            "sent_folder_saved": sent_folder_saved,
            "sent_folder_error": sent_folder_error,
        },
    )


@app.post("/api/thread/{thread_id}")
async def update_thread(thread_id: int, update: ThreadUpdate) -> JSONResponse:
    """Update a thread.

    Args:
        thread_id: Thread ID.
        update: Update data.

    Returns:
        JSON response.
    """
    assert db is not None  # noqa: S101
    thread = await db.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    if update.status:
        await db.update_thread_status(thread_id, update.status)

    return JSONResponse(content={"success": True})


@app.post("/api/sync")
async def sync_emails() -> JSONResponse:
    """Sync emails from configured sources.

    Returns:
        JSON response with sync results.
    """
    assert db is not None  # noqa: S101
    stats = await sync_all_sources(db)

    return JSONResponse(
        content={
            "success": not stats["errors"],
            "synced": stats["new_messages"],
            "errors": stats["errors"],
        },
    )


@app.get("/api/threads")
async def list_threads(status: str | None = None, limit: int = 50, offset: int = 0) -> JSONResponse:
    """Get list of threads.

    Args:
        status: Filter by status.
        limit: Maximum number of threads.
        offset: Number of threads to skip.

    Returns:
        JSON response with threads.
    """
    assert db is not None  # noqa: S101
    threads = await db.get_threads(status=status, limit=limit, offset=offset)
    return JSONResponse(
        content={
            "threads": [
                {
                    "id": t.id,
                    "subject": t.subject,
                    "created_at": t.created_at.isoformat(),
                    "updated_at": t.updated_at.isoformat(),
                    "status": t.status,
                    "is_patch": t.is_patch,
                }
                for t in threads
            ],
        },
    )


@app.get("/api/thread/{thread_id}")
async def get_thread_api(thread_id: int) -> JSONResponse:
    """Get thread details.

    Args:
        thread_id: Thread ID.

    Returns:
        JSON response with thread and messages.
    """
    assert db is not None  # noqa: S101
    thread = await db.get_thread(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")

    return JSONResponse(
        content={
            "id": thread.id,
            "subject": thread.subject,
            "created_at": thread.created_at.isoformat(),
            "updated_at": thread.updated_at.isoformat(),
            "status": thread.status,
            "is_patch": thread.is_patch,
            "messages": [
                {
                    "id": m.id,
                    "message_id": m.message_id,
                    "from_email": m.from_email,
                    "from_name": m.from_name,
                    "subject": m.subject,
                    "date": m.date.isoformat(),
                    "body": m.body,
                    "in_reply_to": m.in_reply_to,
                    "is_patch": m.is_patch,
                }
                for m in thread.messages
            ],
        },
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI application instance.
    """
    return app
