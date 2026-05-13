"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2025-01-15 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "loans",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("member_id", sa.String(32), nullable=False, index=True),
        sa.Column("segment", sa.String(32), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, index=True),
        sa.Column("original_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("current_balance", sa.Numeric(14, 2), nullable=False),
        sa.Column("interest_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("term_months", sa.Integer, nullable=False),
        sa.Column("origination_date", sa.Date, nullable=False),
        sa.Column("maturity_date", sa.Date, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "cecl_assumptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("version", sa.String(32), nullable=False, index=True),
        sa.Column("segment", sa.String(32), nullable=False),
        sa.Column("lifetime_loss_rate", sa.Numeric(6, 4), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
        sa.Column("notes", sa.String(500), nullable=True),
    )

    op.create_table(
        "rate_assumptions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("version", sa.String(32), nullable=False, index=True),
        sa.Column("asset_yield_base", sa.Numeric(6, 4), nullable=False),
        sa.Column("liability_cost_base", sa.Numeric(6, 4), nullable=False),
        sa.Column("total_assets", sa.Numeric(16, 2), nullable=False),
        sa.Column("total_liabilities", sa.Numeric(16, 2), nullable=False),
        sa.Column("asset_duration_years", sa.Numeric(6, 2), nullable=False),
        sa.Column("liability_duration_years", sa.Numeric(6, 2), nullable=False),
        sa.Column("effective_date", sa.Date, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("rate_assumptions")
    op.drop_table("cecl_assumptions")
    op.drop_table("loans")
