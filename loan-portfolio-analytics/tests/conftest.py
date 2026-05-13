"""Test fixtures.

Uses an in-memory SQLite DB for fast unit tests of the analytics services.
Integration tests against Postgres can be added with a docker-postgres fixture.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date
from decimal import Decimal

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.models.loan import (
    CECLAssumption,
    Loan,
    LoanSegment,
    LoanStatus,
    RateAssumption,
)


@pytest_asyncio.fixture
async def session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as s:
        yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def seeded_session(session: AsyncSession) -> AsyncSession:
    """Small deterministic portfolio for math-validation tests."""
    today = date.today()

    loans = [
        Loan(
            member_id="M000001",
            segment=LoanSegment.AUTO_NEW,
            status=LoanStatus.CURRENT,
            original_balance=Decimal("20000.00"),
            current_balance=Decimal("10000.00"),
            interest_rate=Decimal("0.0650"),
            term_months=60,
            origination_date=today,
            maturity_date=today,
        ),
        Loan(
            member_id="M000002",
            segment=LoanSegment.AUTO_NEW,
            status=LoanStatus.CURRENT,
            original_balance=Decimal("30000.00"),
            current_balance=Decimal("20000.00"),
            interest_rate=Decimal("0.0700"),
            term_months=60,
            origination_date=today,
            maturity_date=today,
        ),
        Loan(
            member_id="M000003",
            segment=LoanSegment.UNSECURED,
            status=LoanStatus.DELINQUENT_30,
            original_balance=Decimal("5000.00"),
            current_balance=Decimal("4000.00"),
            interest_rate=Decimal("0.1200"),
            term_months=36,
            origination_date=today,
            maturity_date=today,
        ),
        # Charged-off loan should be excluded from CECL exposure.
        Loan(
            member_id="M000004",
            segment=LoanSegment.UNSECURED,
            status=LoanStatus.CHARGED_OFF,
            original_balance=Decimal("3000.00"),
            current_balance=Decimal("3000.00"),
            interest_rate=Decimal("0.1500"),
            term_months=36,
            origination_date=today,
            maturity_date=today,
        ),
    ]
    session.add_all(loans)

    session.add_all([
        CECLAssumption(
            version="current",
            segment=LoanSegment.AUTO_NEW,
            lifetime_loss_rate=Decimal("0.0100"),
            effective_date=today,
        ),
        CECLAssumption(
            version="current",
            segment=LoanSegment.UNSECURED,
            lifetime_loss_rate=Decimal("0.0500"),
            effective_date=today,
        ),
    ])

    session.add(
        RateAssumption(
            version="current",
            asset_yield_base=Decimal("0.0500"),
            liability_cost_base=Decimal("0.0100"),
            total_assets=Decimal("1000000.00"),
            total_liabilities=Decimal("900000.00"),
            asset_duration_years=Decimal("3.00"),
            liability_duration_years=Decimal("1.00"),
            effective_date=today,
        )
    )

    await session.commit()
    return session
