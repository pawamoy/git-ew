"""Tests for database operations."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from git_ew._internal.database import Database


@pytest.mark.asyncio
async def test_database_init() -> None:
    """Test database initialization."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init_db()
    # If we get here without errors, initialization succeeded
    assert True


@pytest.mark.asyncio
async def test_create_thread() -> None:
    """Test creating a thread."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init_db()

    thread = await db.create_thread(
        subject="Test Thread",
        first_message_id="msg123",
        is_patch=False,
    )

    assert thread.id is not None
    assert thread.subject == "Test Thread"
    assert thread.status == "open"


@pytest.mark.asyncio
async def test_create_message() -> None:
    """Test creating a message."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init_db()

    # Create a thread first
    thread = await db.create_thread(
        subject="Test Thread",
        first_message_id="msg123",
        is_patch=False,
    )

    # Create a message
    message = await db.create_message(
        message_id="msg123",
        thread_id=thread.id,
        from_email="test@example.com",
        from_name="Test User",
        subject="Test Thread",
        date=datetime.now(UTC),
        body="Test message body",
    )

    assert message.id is not None
    assert message.message_id == "msg123"
    assert message.thread_id == thread.id


@pytest.mark.asyncio
async def test_get_threads() -> None:
    """Test getting threads."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init_db()

    # Create some threads
    await db.create_thread("Thread 1", "msg1", is_patch=False)
    await db.create_thread("Thread 2", "msg2", is_patch=True)

    threads = await db.get_threads()
    assert len(threads) == 2


@pytest.mark.asyncio
async def test_get_thread_by_id() -> None:
    """Test getting a thread by ID."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init_db()

    created_thread = await db.create_thread("Test Thread", "msg123", is_patch=False)

    fetched_thread = await db.get_thread(created_thread.id)
    assert fetched_thread is not None
    assert fetched_thread.id == created_thread.id
    assert fetched_thread.subject == "Test Thread"


@pytest.mark.asyncio
async def test_update_thread_status() -> None:
    """Test updating thread status."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init_db()

    thread = await db.create_thread("Test Thread", "msg123", is_patch=False)
    assert thread.status == "open"

    await db.update_thread_status(thread.id, "closed")

    updated_thread = await db.get_thread(thread.id)
    assert updated_thread is not None
    assert updated_thread.status == "closed"


@pytest.mark.asyncio
async def test_config_operations() -> None:
    """Test configuration get/set operations."""
    db = Database("sqlite+aiosqlite:///:memory:")
    await db.init_db()

    # Set a config value
    await db.set_config("test_key", {"value": "test"})

    # Get the config value
    value = await db.get_config("test_key")
    assert value == {"value": "test"}

    # Get non-existent key with default
    value = await db.get_config("nonexistent", "default")
    assert value == "default"
