# Thread organization and rendering utilities for git-ew.

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import markdown
from pymdownx.emoji import to_svg, twemoji

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


def _split_quoted_reply(body: str) -> tuple[str, str]:
    """Split trailing quoted lines from an email body.

    Args:
        body: Email body text.

    Returns:
        The new text and trailing quoted text.
    """
    if not body:
        return "", ""

    lines = body.rstrip().splitlines()
    quote_start_idx = len(lines)
    while quote_start_idx > 0 and lines[quote_start_idx - 1].startswith(">"):
        quote_start_idx -= 1

    return (
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


@dataclass
class _RenderedMessage:
    """Store a message and its presentation-only content."""

    message: Message
    body: str
    quoted_body: str
    children: list[_RenderedMessage]


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


def thread_to_nested_structure(roots: list[ThreadNode]) -> list[_RenderedMessage]:
    """Convert thread tree to nested structure, with single-children popped out to sibling level.

    Also detects and marks quoted sections in message bodies.

    Args:
        roots: List of root ThreadNodes.

    Returns:
        Nested list of messages.
    """
    result: list[_RenderedMessage] = []
    for root in roots:
        body, quoted_body = _split_quoted_reply(root.message.body)
        rendered = _RenderedMessage(
            message=root.message,
            body=body,
            quoted_body=quoted_body,
            children=[],
        )
        if len(root.children) == 1:
            result.append(rendered)
            result.extend(thread_to_nested_structure(root.children))
        elif root.children:
            rendered.children = thread_to_nested_structure(root.children)
            result.append(rendered)
        else:
            result.append(rendered)
    return result
