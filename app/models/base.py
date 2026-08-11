"""
SQLAlchemy declarative base and common mixins.

Every model in the app inherits from Base and uses these mixins
to get consistent UUID primary keys and timestamps.

Usage:
    from app.models.base import Base, UUIDMixin, TimestampMixin

    class User(Base, UUIDMixin, TimestampMixin):
        __tablename__ = "users"
        email = mapped_column(String, unique=True, nullable=False)
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy models.

    DeclarativeBase (SQLAlchemy 2.0) replaces the old declarative_base() factory.
    All models inherit from this class to be registered with the ORM metadata.
    """

    pass


class UUIDMixin:
    """
    Adds a UUID v4 primary key to any model.

    Why UUID over auto-increment?
    - Prevents enumeration attacks (can't guess /users/2 after seeing /users/1)
    - Safe for distributed systems (no central sequence needed)
    - Can be generated client-side (useful for idempotency)

    Trade-off: UUIDs are 16 bytes vs 4 bytes for INT. Acceptable for our scale.
    """

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
        # default runs in Python. server_default would run in SQL.
        # Python-side is fine for UUIDs — deterministic, no DB round-trip.
    )


class TimestampMixin:
    """
    Adds created_at and updated_at timestamps to any model.

    - created_at: set once at INSERT, never changes.
    - updated_at: updated automatically on every UPDATE.

    Both use server_default (DB-side) so timestamps are consistent
    even if the app server clock drifts.
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
