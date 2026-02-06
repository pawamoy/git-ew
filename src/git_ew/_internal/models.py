from __future__ import annotations

from datetime import datetime  # noqa: TC003
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine


class Base(DeclarativeBase):
    """Base class for all models."""


class Thread(Base):
    """Represents an email thread (like a GitHub issue or PR)."""

    __tablename__ = "threads"
    """Database table name."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """Thread unique identifier."""
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    """Thread subject line."""
    first_message_id: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    """ID of the first message in the thread."""
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    """When the thread was created."""
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    """When the thread was last updated."""
    is_patch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    """Whether this thread contains patches."""
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)  # open, closed
    """Thread status (open or closed)."""

    # Relationships
    messages: Mapped[list[Message]] = relationship("Message", back_populates="thread", cascade="all, delete-orphan")
    """Messages in this thread."""


class Message(Base):
    """Represents an individual email message in a thread."""

    __tablename__ = "messages"
    """Database table name."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """Message unique identifier."""
    message_id: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    """Email message ID header."""
    in_reply_to: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    """Message ID this reply refers to."""
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("threads.id"), nullable=False, index=True)
    """Thread this message belongs to."""

    # Email metadata
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    """Sender email address."""
    from_name: Mapped[str] = mapped_column(String(255), nullable=False)
    """Sender name."""
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    """Email subject."""
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    """Email date."""

    # Content
    body: Mapped[str] = mapped_column(Text, nullable=False)
    """Message body text."""
    raw_email: Mapped[str] = mapped_column(Text, nullable=True)
    """Raw email content."""

    # Patch information
    is_patch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    """Whether this message contains a patch."""
    patch_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Extracted patch content."""

    # Relationships
    thread: Mapped[Thread] = relationship("Thread", back_populates="messages")
    """Thread this message belongs to."""


class EmailSource(Base):
    """Represents an email archive source to fetch from."""

    __tablename__ = "email_sources"
    """Database table name."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """Source unique identifier."""
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    """Source name."""
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # maildir, mbox, imap, archive_url
    """Type of email source (maildir, mbox, imap, etc)."""
    config: Mapped[str] = mapped_column(Text, nullable=False)  # JSON config for the source
    """JSON configuration for the source."""
    last_synced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    """When this source was last synced."""
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    """Whether this source is enabled."""


class Configuration(Base):
    """Stores application configuration."""

    __tablename__ = "configuration"
    """Database table name."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """Configuration unique identifier."""
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    """Configuration key."""
    value: Mapped[str] = mapped_column(Text, nullable=False)
    """Configuration value."""


def get_engine(database_url: str = "sqlite+aiosqlite:///./git_ew.db") -> Engine:
    """Create database engine."""
    return create_engine(database_url, echo=False)


def init_db(database_url: str = "sqlite:///./git_ew.db") -> Engine:
    """Initialize the database."""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session_maker(engine: Engine) -> sessionmaker:
    """Get a session maker."""
    return sessionmaker(bind=engine)
