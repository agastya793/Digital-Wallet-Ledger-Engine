"""
Idempotency database model.

Stores idempotency keys permanently to prevent double-execution
of critical financial operations. Moving this to PostgreSQL makes
it immune to Redis cache evictions (LRU policies).
"""

from typing import Any

from sqlalchemy import JSON, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDMixin


class IdempotencyKey(Base, UUIDMixin, TimestampMixin):
    """
    Idempotency key state tracker.

    Fields:
    - user_id + idempotency_key: Unique pair preventing duplicate requests.
    - request_hash: SHA-256 of the request payload to detect key reuse on different data.
    - status: "processing" or "completed".
    - response_code: HTTP status code of the cached response.
    - response_body: JSON payload of the cached response.
    """

    __tablename__ = "idempotency_keys"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "idempotency_key",
            name="uq_user_idempotency_key",
        ),
    )

    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(255), nullable=False)

    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="processing",
    )

    response_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    def __repr__(self) -> str:
        return f"<IdempotencyKey {self.idempotency_key} status={self.status}>"
