# SPDX-License-Identifier: ISC
#
# ISC License
#
# Copyright (c) 2026, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

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
    IMAPFetcher,
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
    thread_to_nested_structure,
)

__all__: list[str] = [
    "Base",
    "CommentCreate",
    "Configuration",
    "Database",
    "EmailFetcher",
    "EmailSender",
    "EmailSource",
    "IMAPFetcher",
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
    "get_engine",
    "get_fetcher",
    "get_parser",
    "get_session_maker",
    "get_thread_api",
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
    "thread_to_nested_structure",
    "update_thread",
    "view_thread",
]
