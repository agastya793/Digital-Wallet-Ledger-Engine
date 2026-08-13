"""
Reconciliation Engine database models.
"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, UUIDMixin


class ReconciliationJob(Base, UUIDMixin):
    """
    Tracks the execution of a reconciliation run.
    """

    __tablename__ = "reconciliation_jobs"

    status: Mapped[str] = mapped_column(String(20), nullable=False, default="running")
    total_wallets_checked: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    discrepancies_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class ReconciliationDiscrepancy(Base, UUIDMixin):
    """
    Records a specific balance mismatch found during a job.
    """

    __tablename__ = "reconciliation_discrepancies"

    job_id: Mapped[str] = mapped_column(
        ForeignKey("reconciliation_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wallet_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)

    expected_balance: Mapped[int] = mapped_column(BigInteger, nullable=False)
    actual_balance: Mapped[int] = mapped_column(BigInteger, nullable=False)
    difference: Mapped[int] = mapped_column(BigInteger, nullable=False)
