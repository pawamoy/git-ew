"""Database models for git-ew."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.engine import Engine


class Base(DeclarativeBase):
    """Base class for all models."""


class Thread(Base):
    """Represents an email thread (like a GitHub issue or PR)."""

    __tablename__ = "threads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    first_message_id: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_patch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="open", nullable=False)  # open, closed

    # Relationships
    messages: Mapped[list[Message]] = relationship("Message", back_populates="thread", cascade="all, delete-orphan")


class Message(Base):
    """Represents an individual email message in a thread."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    message_id: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    in_reply_to: Mapped[str | None] = mapped_column(String(500), nullable=True, index=True)
    thread_id: Mapped[int] = mapped_column(Integer, ForeignKey("threads.id"), nullable=False, index=True)

    # Email metadata
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str] = mapped_column(String(255), nullable=False)
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Content
    body: Mapped[str] = mapped_column(Text, nullable=False)
    raw_email: Mapped[str] = mapped_column(Text, nullable=True)

    # Patch information
    is_patch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    patch_content: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    thread: Mapped[Thread] = relationship("Thread", back_populates="messages")


class EmailSource(Base):
    """Represents an email archive source to fetch from."""

    __tablename__ = "email_sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)  # maildir, mbox, imap, archive_url
    config: Mapped[str] = mapped_column(Text, nullable=False)  # JSON config for the source
    last_synced: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Configuration(Base):
    """Stores application configuration."""

    __tablename__ = "configuration"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)


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
