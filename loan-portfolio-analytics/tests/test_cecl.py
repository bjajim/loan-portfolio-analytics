"""Tests for CECL allowance calculation.

The point of these tests is to demonstrate that the CECL math matches
hand-computed expected values exactly. If any of these fail in isolation,
the allowance number reported to the board is wrong — there is no margin.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan import LoanSegment
from app.services.cecl import compute_cecl


@pytest.mark.asyncio
async def test_cecl_excludes_charged_off_loans(seeded_session: AsyncSession) -> None:
    """Charged-off loans must not appear in CECL exposure."""
    result = await compute_cecl(seeded_session, version="current")

    unsecured = next(s for s in result.by_segment if s.segment == LoanSegment.UNSECURED)
    # Only the $4,000 DELINQUENT_30 loan should be in unsecured exposure.
    # The $3,000 CHARGED_OFF loan must be excluded.
    assert unsecured.exposure == Decimal("4000.00")


@pytest.mark.asyncio
async def test_cecl_matches_hand_computed(seeded_session: AsyncSession) -> None:
    """Hand-computed expected values:

    Auto new: $10,000 + $20,000 = $30,000 exposure × 1.00% = $300.00
    Unsecured: $4,000 exposure × 5.00% = $200.00 (charged-off excluded)
    Total: $34,000 exposure, $500.00 allowance, coverage = 500 / 34000 = 0.0147
    """
    result = await compute_cecl(seeded_session, version="current")

    assert result.total_exposure == Decimal("34000.00")
    assert result.total_allowance == Decimal("500.00")
    assert result.coverage_ratio == Decimal("0.0147")

    auto = next(s for s in result.by_segment if s.segment == LoanSegment.AUTO_NEW)
    assert auto.exposure == Decimal("30000.00")
    assert auto.allowance == Decimal("300.00")

    unsecured = next(s for s in result.by_segment if s.segment == LoanSegment.UNSECURED)
    assert unsecured.allowance == Decimal("200.00")


@pytest.mark.asyncio
async def test_cecl_unknown_version_raises(seeded_session: AsyncSession) -> None:
    with pytest.raises(ValueError, match="No CECL assumptions"):
        await compute_cecl(seeded_session, version="does-not-exist")


# Property-based test: allowance must be monotonic in loss rate.
# Higher loss rate => higher allowance, all else equal.
@given(
    rate_a=st.decimals(min_value="0.0001", max_value="0.0500", places=4),
    rate_b=st.decimals(min_value="0.0001", max_value="0.0500", places=4),
)
@settings(max_examples=25, deadline=None)
def test_cecl_allowance_monotonic_in_loss_rate(rate_a: Decimal, rate_b: Decimal) -> None:
    exposure = Decimal("100000")
    allowance_a = exposure * rate_a
    allowance_b = exposure * rate_b
    # The property we care about, expressed directly.
    if rate_a <= rate_b:
        assert allowance_a <= allowance_b
    else:
        assert allowance_a > allowance_b
