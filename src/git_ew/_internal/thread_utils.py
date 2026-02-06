"""Thread organization and rendering utilities for git-ew."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from git_ew._internal.models import Message


@dataclass
class ThreadNode:
    """Represents a node in a thread tree."""

    message: Message
    children: list[ThreadNode]
    depth: int = 0
    can_flatten: bool = False

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


def flatten_linear_chains(roots: list[ThreadNode]) -> list[ThreadNode]:
    """Flatten linear chains in the thread tree.

    A linear chain is a sequence of messages where each message has exactly one reply.
    These can be flattened for better readability.

    Args:
        roots: List of root ThreadNodes.

    Returns:
        List of ThreadNodes with linear chains flattened.
    """

    def flatten_node(node: ThreadNode) -> list[ThreadNode]:
        """Flatten a node and its children.

        Returns a flat list of nodes representing the flattened chain.
        """
        result = [node]

        # If this node has exactly one child, continue the chain
        if len(node.children) == 1:
            child = node.children[0]
            # Recursively flatten the child
            flattened_child = flatten_node(child)
            result.extend(flattened_child)
            # Clear children since we've flattened them
            node.children = []
        else:
            # Multiple children or no children - recursively flatten each child
            for child in node.children:
                flatten_node(child)

        return result

    # For rendering purposes, we don't actually modify the tree structure,
    # we just mark nodes that can be flattened
    def mark_flattenable(node: ThreadNode) -> bool:
        """Mark nodes that are part of a linear chain.

        Returns True if this node is part of a linear chain.
        """
        if len(node.children) == 0:
            return True
        if len(node.children) == 1:
            child_is_linear = mark_flattenable(node.children[0])
            node.can_flatten = child_is_linear
            return True
        # Multiple children - not linear
        node.can_flatten = False
        for child in node.children:
            mark_flattenable(child)
        return False

    for root in roots:
        mark_flattenable(root)

    return roots


def thread_to_flat_list(roots: list[ThreadNode], *, flatten: bool = True) -> list[dict[str, Any]]:
    """Convert thread tree to a flat list for rendering.

    Args:
        roots: List of root ThreadNodes.
        flatten: Whether to flatten linear chains.

    Returns:
        List of dictionaries with message data and rendering hints.
    """
    if flatten:
        roots = flatten_linear_chains(roots)

    result = []

    def traverse(node: ThreadNode, *, in_flattened_chain: bool = False) -> None:
        """Traverse the tree and build the flat list."""
        # Determine if we should show this node as flattened
        show_flattened = flatten and node.can_flatten and len(node.children) == 1

        result.append(
            {
                "message": node.message,
                "depth": node.depth,
                "can_flatten": node.can_flatten,
                "show_flattened": show_flattened,
                "in_flattened_chain": in_flattened_chain,
                "has_children": len(node.children) > 0,
                "num_children": len(node.children),
            },
        )

        # Traverse children
        for child in node.children:
            traverse(child, in_flattened_chain=show_flattened)

    for root in roots:
        traverse(root)

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
