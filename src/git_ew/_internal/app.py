"""FastAPI web application for git-ew."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from git_ew._internal.database import Database
from git_ew._internal.email_fetcher import get_fetcher
from git_ew._internal.email_sender import create_email_sender
from git_ew._internal.thread_utils import build_thread_tree, thread_to_flat_list

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

# Global database instance
db: Database | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Application lifespan manager."""
    global db  # noqa: PLW0603
    db = Database()
    await db.init_db()
    yield
    # Cleanup if needed


app = FastAPI(title="git-ew", description="Git Email Workflow", lifespan=lifespan)

# Setup templates
template_dir = Path(__file__).parent / "templates"
template_dir.mkdir(exist_ok=True)
templates = Jinja2Templates(directory=str(template_dir))

# Setup static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# Pydantic models for API
class CommentCreate(BaseModel):
    """Model for creating a comment."""

    body: str
    in_reply_to: str | None = None


class ThreadUpdate(BaseModel):
    """Model for updating a thread."""

    status: str | None = None


# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request, status: str = "open") -> HTMLResponse:
    """Show list of threads (pull requests/issues).

    Args:
        request: FastAPI request.
        status: Filter by status (open/closed).

    Returns:
        HTML response.
    """
    assert db is not None  # noqa: S101
    threads = await db.get_threads(status=status)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "threads": threads,
            "current_status": status,
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
    flat_list = thread_to_flat_list(tree, flatten=flatten)

    return templates.TemplateResponse(
        "thread.html",
        {
            "request": request,
            "thread": thread,
            "messages": flat_list,
            "flatten": flatten,
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

    # Determine recipient and references
    if comment.in_reply_to:
        # Get the message we're replying to
        reply_to_msg = await db.get_message_by_id(comment.in_reply_to)
        if not reply_to_msg:
            raise HTTPException(status_code=404, detail="Reply-to message not found")

        to_email = reply_to_msg.from_email
        subject = reply_to_msg.subject

        # Build references list
        references = [thread.first_message_id]
        if reply_to_msg.message_id != thread.first_message_id:
            references.append(reply_to_msg.message_id)
    else:
        # Reply to the first message in the thread
        first_msg = next((m for m in thread.messages if m.message_id == thread.first_message_id), None)
        if not first_msg:
            raise HTTPException(status_code=404, detail="First message not found")

        to_email = first_msg.from_email
        subject = thread.subject
        references = [thread.first_message_id]

    # Send the email
    try:
        message_id = sender.send_reply(
            to_email=to_email,
            subject=subject,
            body=comment.body,
            in_reply_to=comment.in_reply_to or thread.first_message_id,
            references=references,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {e}") from e

    # Store in database
    message = await db.create_message(
        message_id=message_id,
        thread_id=thread_id,
        from_email=email_config["from_email"],
        from_name=email_config.get("from_name", email_config["from_email"]),
        subject=subject,
        date=datetime.now(UTC),
        body=comment.body,
        in_reply_to=comment.in_reply_to or thread.first_message_id,
    )

    return JSONResponse(
        content={
            "message_id": message.message_id,
            "success": True,
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
    sources = await db.get_email_sources()
    total_synced = 0

    for source in sources:
        if not source.enabled:
            continue

        try:
            config = json.loads(source.config)
            fetcher = get_fetcher(source.source_type, config)

            async for parsed_email in fetcher.fetch_emails():  # ty: ignore[not-iterable]
                # Check if message already exists
                existing = await db.get_message_by_id(parsed_email.message_id)
                if existing:
                    continue

                # Find or create thread
                thread_id_str = parsed_email.get_thread_id()
                thread = await db.get_thread_by_message_id(thread_id_str)

                if not thread:
                    # Create new thread
                    thread = await db.create_thread(
                        subject=parsed_email.clean_subject,
                        first_message_id=thread_id_str,
                        is_patch=parsed_email.is_patch,
                    )

                # Create message
                await db.create_message(
                    message_id=parsed_email.message_id,
                    thread_id=thread.id,
                    from_email=parsed_email.from_email,
                    from_name=parsed_email.from_name,
                    subject=parsed_email.subject,
                    date=parsed_email.date,
                    body=parsed_email.body,
                    in_reply_to=parsed_email.in_reply_to,
                    is_patch=parsed_email.is_patch,
                    patch_content=parsed_email.patch_content,
                    raw_email=parsed_email.raw,
                )

                total_synced += 1

        except Exception:  # noqa: BLE001, S112
            # Log error but continue with other sources
            continue

    return JSONResponse(
        content={
            "success": True,
            "synced": total_synced,
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
