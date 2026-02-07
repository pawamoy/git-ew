# Thread organization and rendering utilities for git-ew.

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any

import markdown
from pymdownx.emoji import twemoji, to_svg

if TYPE_CHECKING:
    from git_ew._internal.models import Message

# Markdown instance with configured extensions
_md = markdown.Markdown(
    extensions=[
        "abbr",
        "admonition",
        "attr_list",
        "def_list",
        "footnotes",
        "md_in_html",
        "nl2br",
        "toc",
        "pymdownx.arithmatex",
        "pymdownx.betterem",
        "pymdownx.caret",
        "pymdownx.details",
        "pymdownx.emoji",
        "pymdownx.highlight",
        "pymdownx.inlinehilite",
        "pymdownx.keys",
        "pymdownx.magiclink",
        "pymdownx.mark",
        "pymdownx.smartsymbols",
        "pymdownx.superfences",
        "pymdownx.tabbed",
        "pymdownx.tasklist",
        "pymdownx.tilde",
    ],
    extension_configs={
        "toc": {"permalink": True},
        "pymdownx.arithmatex": {"generic": True},
        "pymdownx.betterem": {"smart_enable": "all"},
        "pymdownx.emoji": {
            "emoji_index": twemoji,
            "emoji_generator": to_svg,
        },
        "pymdownx.tabbed": {"alternate_style": True},
        "pymdownx.tasklist": {"custom_checkbox": True},
    },
)


def render_markdown(text: str) -> str:
    """Render plain text as markdown HTML.

    Args:
        text: Plain text to render.

    Returns:
        HTML string.
    """
    _md.reset()
    return _md.convert(text)


def detect_quoted_reply(message: Message) -> None:
    """Detect and split quoted sections from email body.

    Args:
        body: The email body text.
        parent_body: The parent message body for comparison (if available).
    """
    if not message.body:
        message.body = ("", "")

    # Starting from end, climb up lines until not quoted
    lines = message.body.rstrip().splitlines()
    quote_start_idx = len(lines)
    while lines[quote_start_idx - 1].startswith(">") and quote_start_idx > 0:
        quote_start_idx -= 1

    # Split the content
    if quote_start_idx is not None and quote_start_idx > 0:
        message.body = (
            # TODO: Option to render Markdown.
            "\n".join(lines[:quote_start_idx]).strip(),
            "\n".join(lines[quote_start_idx:]).strip(),
        )


@dataclass
class ThreadNode:
    """Represents a node in a thread tree."""

    message: Message
    """The message at this node."""
    children: list[ThreadNode]
    """Child nodes in the thread tree."""


def build_thread_tree(messages: list[Message]) -> list[ThreadNode]:
    """Build a tree structure from a flat list of messages.

    Args:
        messages: List of messages in the thread.

    Returns:
        List of root ThreadNodes.
    """
    # Create nodes for each message
    nodes = {msg.message_id: ThreadNode(message=msg, children=[]) for msg in messages}

    # Build the tree by linking children to parents
    roots = []

    for msg in messages:
        node = nodes[msg.message_id]

        if msg.in_reply_to and msg.in_reply_to in nodes:
            # This message is a reply to another message
            parent_node = nodes[msg.in_reply_to]
            parent_node.children.append(node)
        else:
            # This is a root message
            roots.append(node)

    return roots


def thread_to_nested_structure(roots: list[ThreadNode]) -> list[dict[str, Any]]:
    """Convert thread tree to nested structure, with single-children popped out to sibling level.

    Also detects and marks quoted sections in message bodies.

    Args:
        roots: List of root ThreadNodes.

    Returns:
        Nested list of messages.
    """
    result: list[dict[str, Any]] = []
    for root in roots:
        detect_quoted_reply(root.message)
        if len(root.children) == 1:
            result.append({"message": root.message})
            result.extend(thread_to_nested_structure(root.children))
        elif root.children:
            result.append({
                "message": root.message,
                "children": thread_to_nested_structure(root.children),
            })
        else:
            result.append({"message": root.message})
    return result
