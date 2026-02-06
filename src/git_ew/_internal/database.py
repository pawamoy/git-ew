# Database operations for git-ew.

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from git_ew._internal.models import Base, Configuration, EmailSource, Message, Thread

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


class Database:
    """Database manager."""

    def __init__(self, database_url: str = "sqlite+aiosqlite:///./git_ew.db"):
        """Initialize database manager.

        Args:
            database_url: Database connection URL.
        """
        self.engine = create_async_engine(database_url, echo=False)
        """SQLAlchemy async engine instance."""
        self.session_maker = async_sessionmaker(self.engine, class_=AsyncSession, expire_on_commit=False)
        """Async session factory."""

    async def init_db(self) -> None:
        """Initialize database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Get a database session."""
        async with self.session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    async def get_threads(
        self,
        status: str | None = None,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Thread]:
        """Get threads with optional filtering.

        Args:
            status: Filter by status (open/closed).
            limit: Maximum number of threads to return.
            offset: Number of threads to skip.

        Returns:
            List of threads.
        """
        async with self.session() as session:
            query = select(Thread).order_by(Thread.updated_at.desc())
            if status:
                query = query.where(Thread.status == status)
            if limit is not None:
                query = query.limit(limit)
            query = query.offset(offset)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def get_thread(self, thread_id: int) -> Thread | None:
        """Get a thread by ID with all messages.

        Args:
            thread_id: Thread ID.

        Returns:
            Thread or None if not found.
        """
        async with self.session() as session:
            query = select(Thread).where(Thread.id == thread_id).options(selectinload(Thread.messages))
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_thread_by_message_id(self, message_id: str) -> Thread | None:
        """Get a thread by first message ID.

        Args:
            message_id: Message ID.

        Returns:
            Thread or None if not found.
        """
        async with self.session() as session:
            query = select(Thread).where(Thread.first_message_id == message_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def create_thread(
        self,
        subject: str,
        first_message_id: str,
        *,
        is_patch: bool = False,
    ) -> Thread:
        """Create a new thread.

        Args:
            subject: Thread subject.
            first_message_id: ID of the first message.
            is_patch: Whether this thread contains patches.

        Returns:
            Created thread.
        """
        now = datetime.now(UTC)
        thread = Thread(
            subject=subject,
            first_message_id=first_message_id,
            created_at=now,
            updated_at=now,
            is_patch=is_patch,
            status="open",
        )
        async with self.session() as session:
            session.add(thread)
            await session.flush()
            await session.refresh(thread)
            return thread

    async def create_message(
        self,
        message_id: str,
        thread_id: int,
        from_email: str,
        from_name: str,
        subject: str,
        date: datetime,
        body: str,
        *,
        in_reply_to: str | None = None,
        is_patch: bool = False,
        patch_content: str | None = None,
        raw_email: str | None = None,
    ) -> Message:
        """Create a new message.

        Args:
            message_id: Unique message ID.
            thread_id: Thread ID this message belongs to.
            from_email: Sender email.
            from_name: Sender name.
            subject: Message subject.
            date: Message date.
            body: Message body.
            in_reply_to: ID of message this replies to.
            is_patch: Whether this message contains a patch.
            patch_content: Patch content if applicable.
            raw_email: Raw email content.

        Returns:
            Created message.
        """
        message = Message(
            message_id=message_id,
            thread_id=thread_id,
            from_email=from_email,
            from_name=from_name,
            subject=subject,
            date=date,
            body=body,
            in_reply_to=in_reply_to,
            is_patch=is_patch,
            patch_content=patch_content,
            raw_email=raw_email,
        )
        async with self.session() as session:
            session.add(message)

            # Update thread's updated_at
            thread = await session.get(Thread, thread_id)
            if thread:
                thread.updated_at = datetime.now(UTC)

            await session.flush()
            await session.refresh(message)
            return message

    async def get_message_by_id(self, message_id: str) -> Message | None:
        """Get a message by its message ID.

        Args:
            message_id: Message ID.

        Returns:
            Message or None if not found.
        """
        async with self.session() as session:
            query = select(Message).where(Message.message_id == message_id)
            result = await session.execute(query)
            return result.scalar_one_or_none()

    async def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        async with self.session() as session:
            query = select(Configuration).where(Configuration.key == key)
            result = await session.execute(query)
            config = result.scalar_one_or_none()
            if config:
                return json.loads(config.value)
            return default

    async def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key.
            value: Configuration value.
        """
        async with self.session() as session:
            query = select(Configuration).where(Configuration.key == key)
            result = await session.execute(query)
            config = result.scalar_one_or_none()

            if config:
                config.value = json.dumps(value)
            else:
                config = Configuration(key=key, value=json.dumps(value))
                session.add(config)

    async def get_email_sources(self) -> list[EmailSource]:
        """Get all email sources.

        Returns:
            List of email sources.
        """
        async with self.session() as session:
            query = select(EmailSource)
            result = await session.execute(query)
            return list(result.scalars().all())

    async def update_thread_status(self, thread_id: int, status: str) -> None:
        """Update thread status.

        Args:
            thread_id: Thread ID.
            status: New status (open/closed).
        """
        async with self.session() as session:
            thread = await session.get(Thread, thread_id)
            if thread:
                thread.status = status
                thread.updated_at = datetime.now(UTC)
