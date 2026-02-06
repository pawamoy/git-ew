# Thread organization and rendering utilities for git-ew.

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from git_ew._internal.models import Message


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
    depth: int = 0
    """Depth in the tree."""
    can_flatten: bool = False
    """Whether this node can be flattened."""

    def __post_init__(self):
        """Calculate if this node can be flattened."""
        # A node can be flattened if it has exactly one child and that child can also be flattened
        # or if it has exactly one child that is a leaf
        if len(self.children) == 1:
            self.can_flatten = True
        else:
            self.can_flatten = False


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

    # Set depths
    def set_depths(node: ThreadNode, depth: int = 0) -> None:
        node.depth = depth
        for child in node.children:
            set_depths(child, depth + 1)

    for root in roots:
        set_depths(root)

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


def group_by_thread_subject(messages: list[Message]) -> dict[str, list[Message]]:
    """Group messages by thread subject.

    Args:
        messages: List of messages.
    """

    def clean_subject(subject: str) -> str:
        """Clean subject line for grouping."""
        # Remove RE:, Re:, FWD:, etc.
        subject = re.sub(r"^(RE|Re|FW|Fw|FWD|Fwd):\s*", "", subject, flags=re.IGNORECASE)
        # Remove [tag] prefixes
        subject = re.sub(r"^\[.*?\]\s*", "", subject)
        return subject.strip().lower()

    groups = {}
    for msg in messages:
        clean = clean_subject(msg.subject)
        if clean not in groups:
            groups[clean] = []
        groups[clean].append(msg)

    return groups
