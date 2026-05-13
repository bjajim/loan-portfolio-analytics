"""Portfolio summary and KPI calculations."""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan import Loan, LoanStatus
from app.schemas.analytics import PortfolioSummary

_DELINQUENT_STATUSES = frozenset(
    {LoanStatus.DELINQUENT_30, LoanStatus.DELINQUENT_60, LoanStatus.DELINQUENT_90}
)
_ACTIVE_STATUSES = frozenset(
    {
        LoanStatus.CURRENT,
        LoanStatus.DELINQUENT_30,
        LoanStatus.DELINQUENT_60,
        LoanStatus.DELINQUENT_90,
    }
)


async def portfolio_summary(session: AsyncSession) -> PortfolioSummary:
    stmt = select(Loan).where(Loan.status.in_([s.value for s in _ACTIVE_STATUSES]))
    loans = (await session.execute(stmt)).scalars().all()

    total_balance = Decimal("0")
    by_segment: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    by_status: dict[str, int] = defaultdict(int)
    weighted_rate_num = Decimal("0")
    delinquent_balance = Decimal("0")

    for loan in loans:
        total_balance += loan.current_balance
        # SQLAlchemy may return the column as a plain str rather than the
        # StrEnum instance — handle both.
        segment_key = loan.segment.value if hasattr(loan.segment, "value") else str(loan.segment)
        status_key = loan.status.value if hasattr(loan.status, "value") else str(loan.status)
        by_segment[segment_key] += loan.current_balance
        by_status[status_key] += 1
        weighted_rate_num += loan.current_balance * loan.interest_rate
        if status_key in {s.value for s in _DELINQUENT_STATUSES}:
            delinquent_balance += loan.current_balance

    weighted_avg_rate = (
        (weighted_rate_num / total_balance).quantize(Decimal("0.0001"))
        if total_balance > 0
        else Decimal("0")
    )
    delinquency_rate = (
        (delinquent_balance / total_balance).quantize(Decimal("0.0001"))
        if total_balance > 0
        else Decimal("0")
    )

    return PortfolioSummary(
        total_loans=len(loans),
        total_balance=total_balance,
        by_segment=dict(by_segment),
        by_status=dict(by_status),
        delinquency_rate=delinquency_rate,
        weighted_avg_rate=weighted_avg_rate,
    )
