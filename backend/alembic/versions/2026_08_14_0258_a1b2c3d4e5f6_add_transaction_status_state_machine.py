"""add_transaction_status_state_machine

Revision ID: a1b2c3d4e5f6
Revises: 6792e5f624e3
Create Date: 2026-08-14 02:58:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "6792e5f624e3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add pending_operations JSONB column
    op.add_column(
        "transactions",
        sa.Column(
            "pending_operations", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )

    # Add status check constraint
    op.create_check_constraint(
        "chk_transaction_status",
        "transactions",
        "status IN ('pending', 'processing', 'completed', 'failed', 'reversed', 'refunded')",
    )


def downgrade() -> None:
    # Drop status check constraint
    op.drop_constraint("chk_transaction_status", "transactions", type_="check")

    # Drop pending_operations JSONB column
    op.drop_column("transactions", "pending_operations")
