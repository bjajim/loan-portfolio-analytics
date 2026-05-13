"""Seed a realistic 500-loan portfolio plus CECL and ALM assumptions.

Run with: python -m scripts.seed
"""

from __future__ import annotations

import asyncio
import random
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import delete

from app.db.session import AsyncSessionLocal, engine
from app.models.loan import (
    CECLAssumption,
    Loan,
    LoanSegment,
    LoanStatus,
    RateAssumption,
)

random.seed(42)  # deterministic seed for reproducibility

# Realistic profile for a small federally chartered credit union.
SEGMENT_MIX = {
    LoanSegment.AUTO_NEW: 0.20,
    LoanSegment.AUTO_USED: 0.30,
    LoanSegment.UNSECURED: 0.15,
    LoanSegment.REAL_ESTATE: 0.25,
    LoanSegment.CREDIT_CARD: 0.10,
}

SEGMENT_RATES: dict[LoanSegment, tuple[Decimal, Decimal]] = {
    LoanSegment.AUTO_NEW: (Decimal("0.0599"), Decimal("0.0899")),
    LoanSegment.AUTO_USED: (Decimal("0.0699"), Decimal("0.1199")),
    LoanSegment.UNSECURED: (Decimal("0.0999"), Decimal("0.1599")),
    LoanSegment.REAL_ESTATE: (Decimal("0.0625"), Decimal("0.0775")),
    LoanSegment.CREDIT_CARD: (Decimal("0.1499"), Decimal("0.2199")),
}

SEGMENT_TERMS = {
    LoanSegment.AUTO_NEW: (48, 72),
    LoanSegment.AUTO_USED: (36, 60),
    LoanSegment.UNSECURED: (24, 60),
    LoanSegment.REAL_ESTATE: (180, 360),
    LoanSegment.CREDIT_CARD: (12, 12),
}

SEGMENT_AMOUNTS: dict[LoanSegment, tuple[int, int]] = {
    LoanSegment.AUTO_NEW: (15_000, 45_000),
    LoanSegment.AUTO_USED: (8_000, 28_000),
    LoanSegment.UNSECURED: (2_000, 25_000),
    LoanSegment.REAL_ESTATE: (75_000, 350_000),
    LoanSegment.CREDIT_CARD: (500, 12_000),
}

# CECL lifetime loss rates per segment (vintage methodology).
CECL_RATES = {
    LoanSegment.AUTO_NEW: Decimal("0.0085"),     # 0.85%
    LoanSegment.AUTO_USED: Decimal("0.0150"),    # 1.50%
    LoanSegment.UNSECURED: Decimal("0.0350"),    # 3.50%
    LoanSegment.REAL_ESTATE: Decimal("0.0035"),  # 0.35%
    LoanSegment.CREDIT_CARD: Decimal("0.0425"),  # 4.25%
}

# Realistic delinquency distribution.
STATUS_DISTRIBUTION = [
    (LoanStatus.CURRENT, 0.94),
    (LoanStatus.DELINQUENT_30, 0.03),
    (LoanStatus.DELINQUENT_60, 0.015),
    (LoanStatus.DELINQUENT_90, 0.01),
    (LoanStatus.CHARGED_OFF, 0.005),
]


def _pick_segment() -> LoanSegment:
    r = random.random()
    cumulative = 0.0
    for segment, weight in SEGMENT_MIX.items():
        cumulative += weight
        if r <= cumulative:
            return segment
    return LoanSegment.AUTO_USED


def _pick_status() -> LoanStatus:
    r = random.random()
    cumulative = 0.0
    for status, weight in STATUS_DISTRIBUTION:
        cumulative += weight
        if r <= cumulative:
            return status
    return LoanStatus.CURRENT


def _generate_loan(loan_id: int) -> Loan:
    segment = _pick_segment()
    rate_lo, rate_hi = SEGMENT_RATES[segment]
    term_lo, term_hi = SEGMENT_TERMS[segment]
    amt_lo, amt_hi = SEGMENT_AMOUNTS[segment]

    original = Decimal(random.randint(amt_lo, amt_hi))
    paid_pct = Decimal(random.uniform(0.05, 0.85)).quantize(Decimal("0.01"))
    current = (original * (Decimal("1") - paid_pct)).quantize(Decimal("0.01"))

    term = random.randint(term_lo, term_hi)
    months_elapsed = random.randint(1, max(term - 1, 1))
    origination = date.today() - timedelta(days=months_elapsed * 30)
    maturity = origination + timedelta(days=term * 30)

    return Loan(
        member_id=f"M{loan_id:06d}",
        segment=segment,
        status=_pick_status(),
        original_balance=original,
        current_balance=current,
        interest_rate=Decimal(random.uniform(float(rate_lo), float(rate_hi))).quantize(
            Decimal("0.0001")
        ),
        term_months=term,
        origination_date=origination,
        maturity_date=maturity,
    )


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        # Idempotent: clear and reseed.
        await session.execute(delete(Loan))
        await session.execute(delete(CECLAssumption))
        await session.execute(delete(RateAssumption))

        # Loans
        loans = [_generate_loan(i) for i in range(1, 501)]
        session.add_all(loans)

        # CECL assumptions
        today = date.today()
        for segment, rate in CECL_RATES.items():
            session.add(
                CECLAssumption(
                    version="current",
                    segment=segment,
                    lifetime_loss_rate=rate,
                    effective_date=today,
                    notes="Seed vintage assumption — internal benchmark.",
                )
            )

        # Rate assumptions
        session.add(
            RateAssumption(
                version="current",
                asset_yield_base=Decimal("0.0575"),
                liability_cost_base=Decimal("0.0145"),
                total_assets=Decimal("12500000.00"),
                total_liabilities=Decimal("11000000.00"),
                asset_duration_years=Decimal("3.20"),
                liability_duration_years=Decimal("1.40"),
                effective_date=today,
            )
        )

        await session.commit()
        print(f"Seeded {len(loans)} loans + CECL/ALM assumptions.")


async def main() -> None:
    await seed()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
