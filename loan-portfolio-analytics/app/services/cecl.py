"""CECL (Current Expected Credit Loss) allowance calculation.

Implements the vintage methodology: applies a configured lifetime loss rate
per loan segment against the amortized cost basis (current balance) of the
portfolio. This is the most defensible approach for institutions without
enough internal data for PD/LGD or DCF modeling.

The interface is structured so additional methods (PD/LGD, DCF, WARM) can
be added as separate implementations behind ``CECLMethod`` without changing
the API or callers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan import CECLAssumption, Loan, LoanSegment, LoanStatus
from app.schemas.analytics import CECLResult, CECLSegmentResult

# Loans in these statuses are excluded from CECL exposure: charged-off loans
# are already losses (separately tracked), and paid-off loans have no exposure.
_EXCLUDED_STATUSES = frozenset({LoanStatus.CHARGED_OFF, LoanStatus.PAID_OFF})


class CECLMethod(ABC):
    """Abstract CECL methodology. Add new methods (PD/LGD, DCF) here."""

    @abstractmethod
    async def compute(self, session: AsyncSession, version: str) -> CECLResult: ...


class VintageMethod(CECLMethod):
    """Vintage methodology: lifetime loss rate per segment × exposure."""

    async def compute(self, session: AsyncSession, version: str) -> CECLResult:
        loss_rates = await self._load_loss_rates(session, version)
        exposures = await self._exposure_by_segment(session)

        segment_results: list[CECLSegmentResult] = []
        total_exposure = Decimal("0")
        total_allowance = Decimal("0")

        for segment, exposure in sorted(exposures.items()):
            rate = loss_rates.get(segment)
            if rate is None:
                # No assumption configured for this segment — surface it as
                # zero allowance rather than silently dropping the exposure.
                rate = Decimal("0")
            allowance = (exposure * rate).quantize(Decimal("0.01"))
            segment_results.append(
                CECLSegmentResult(
                    segment=segment,
                    exposure=exposure,
                    loss_rate=rate,
                    allowance=allowance,
                )
            )
            total_exposure += exposure
            total_allowance += allowance

        coverage = (
            (total_allowance / total_exposure).quantize(Decimal("0.0001"))
            if total_exposure > 0
            else Decimal("0")
        )

        return CECLResult(
            assumption_version=version,
            total_exposure=total_exposure,
            total_allowance=total_allowance,
            coverage_ratio=coverage,
            by_segment=segment_results,
        )

    async def _load_loss_rates(
        self, session: AsyncSession, version: str
    ) -> dict[LoanSegment, Decimal]:
        stmt = select(CECLAssumption).where(CECLAssumption.version == version)
        rows = (await session.execute(stmt)).scalars().all()
        if not rows:
            raise ValueError(f"No CECL assumptions found for version '{version}'")
        return {
            (row.segment if isinstance(row.segment, LoanSegment) else LoanSegment(row.segment)): row.lifetime_loss_rate
            for row in rows
        }

    async def _exposure_by_segment(
        self, session: AsyncSession
    ) -> dict[LoanSegment, Decimal]:
        stmt = select(Loan).where(Loan.status.notin_([s.value for s in _EXCLUDED_STATUSES]))
        loans = (await session.execute(stmt)).scalars().all()
        totals: dict[LoanSegment, Decimal] = defaultdict(lambda: Decimal("0"))
        for loan in loans:
            # Normalize to enum regardless of how SQLAlchemy hydrates it.
            segment = (
                loan.segment
                if isinstance(loan.segment, LoanSegment)
                else LoanSegment(loan.segment)
            )
            totals[segment] += loan.current_balance
        return dict(totals)


# Default method used by the API. Inject via DI in tests if you need to mock.
default_method: CECLMethod = VintageMethod()


async def compute_cecl(
    session: AsyncSession,
    version: str = "current",
    method: CECLMethod | None = None,
) -> CECLResult:
    """Top-level entry point used by the API layer."""
    return await (method or default_method).compute(session, version)
