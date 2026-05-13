"""Tests for portfolio summary KPI calculation."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.portfolio import portfolio_summary


@pytest.mark.asyncio
async def test_portfolio_summary_excludes_charged_off(seeded_session: AsyncSession) -> None:
    """
    Active loans only:
      Auto new: $10,000 + $20,000 = $30,000 (both CURRENT)
      Unsecured: $4,000 (DELINQUENT_30)
    Total = $34,000 across 3 loans.

    Weighted avg rate = (10000×0.0650 + 20000×0.0700 + 4000×0.1200) / 34000
                     = (650 + 1400 + 480) / 34000
                     = 2530 / 34000
                     = 0.0744
    """
    result = await portfolio_summary(seeded_session)
    assert result.total_loans == 3
    assert result.total_balance == Decimal("34000.00")
    assert result.weighted_avg_rate == Decimal("0.0744")


@pytest.mark.asyncio
async def test_portfolio_summary_delinquency_rate(seeded_session: AsyncSession) -> None:
    """Delinquent balance = $4,000 (unsecured DELINQUENT_30) out of $34,000 active."""
    result = await portfolio_summary(seeded_session)
    expected = (Decimal("4000") / Decimal("34000")).quantize(Decimal("0.0001"))
    assert result.delinquency_rate == expected


@pytest.mark.asyncio
async def test_portfolio_summary_segment_breakdown(seeded_session: AsyncSession) -> None:
    result = await portfolio_summary(seeded_session)
    assert result.by_segment["auto_new"] == Decimal("30000.00")
    assert result.by_segment["unsecured"] == Decimal("4000.00")
    # Charged-off does not contribute to either count or balance.
    assert "charged_off" not in result.by_segment
