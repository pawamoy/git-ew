"""git-ew package.

Git Email Workflow
"""

from __future__ import annotations

from git_ew._internal.app import (
    CommentCreate,
    ThreadUpdate,
    app,
    create_app,
    db,
    get_thread_api,
    index,
    lifespan,
    list_threads,
    post_comment,
    static_dir,
    sync_emails,
    template_dir,
    templates,
    update_thread,
    view_thread,
)
from git_ew._internal.cli import get_parser, main
from git_ew._internal.database import Database
from git_ew._internal.email_fetcher import (
    EmailFetcher,
    MaildirFetcher,
    MboxFetcher,
    PublicInboxFetcher,
    get_fetcher,
)
from git_ew._internal.email_parser import (
    ParsedEmail,
    extract_quoted_text,
    normalize_message_id,
    parse_email,
)
from git_ew._internal.email_sender import EmailSender, create_email_sender
from git_ew._internal.models import (
    Base,
    Configuration,
    EmailSource,
    Message,
    Thread,
    get_engine,
    get_session_maker,
    init_db,
)
from git_ew._internal.sync import sync_all_sources, sync_command
from git_ew._internal.thread_utils import (
    ThreadNode,
    build_thread_tree,
    flatten_linear_chains,
    group_by_thread_subject,
    thread_to_flat_list,
)

__all__: list[str] = [
    "Base",
    "CommentCreate",
    "Configuration",
    "Database",
    "EmailFetcher",
    "EmailSender",
    "EmailSource",
    "MaildirFetcher",
    "MboxFetcher",
    "Message",
    "ParsedEmail",
    "PublicInboxFetcher",
    "Thread",
    "ThreadNode",
    "ThreadUpdate",
    "app",
    "build_thread_tree",
    "create_app",
    "create_email_sender",
    "db",
    "extract_quoted_text",
    "flatten_linear_chains",
    "get_engine",
    "get_fetcher",
    "get_parser",
    "get_session_maker",
    "get_thread_api",
    "group_by_thread_subject",
    "index",
    "init_db",
    "lifespan",
    "list_threads",
    "main",
    "normalize_message_id",
    "parse_email",
    "post_comment",
    "static_dir",
    "sync_all_sources",
    "sync_command",
    "sync_emails",
    "template_dir",
    "templates",
    "thread_to_flat_list",
    "update_thread",
    "view_thread",
]
