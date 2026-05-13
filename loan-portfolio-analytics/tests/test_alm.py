"""Tests for ALM rate-shock calculation."""

from __future__ import annotations

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.alm import compute_alm


@pytest.mark.asyncio
async def test_alm_base_case_matches_hand_computed(seeded_session: AsyncSession) -> None:
    """
    Base case from seeded_session fixture:
      assets = $1,000,000 @ 5.00% yield
      liabilities = $900,000 @ 1.00% cost
      NII = (1,000,000 × 0.05) - (900,000 × 0.01) = 50,000 - 9,000 = $41,000
      NEV = 1,000,000 - 900,000 = $100,000
    """
    result = await compute_alm(seeded_session, version="current")

    assert result.base_case.shock_bps == 0
    assert result.base_case.net_interest_income_12mo == Decimal("41000.00")
    assert result.base_case.net_economic_value == Decimal("100000.00")


@pytest.mark.asyncio
async def test_alm_up_200_bps(seeded_session: AsyncSession) -> None:
    """
    +200 bps shock on both asset yield and liability cost:
      asset yield = 5.00% + 2.00% = 7.00%
      liability cost = 1.00% + 2.00% = 3.00%
      NII = (1,000,000 × 0.07) - (900,000 × 0.03) = 70,000 - 27,000 = $43,000
      EaR delta = (43,000 - 41,000) / 41,000 = +4.88% (rounded)

    NEV under +200 bps with duration approach:
      Δrate = +0.02
      ΔV_assets = -3.0 × 0.02 × 1,000,000 = -$60,000
      ΔV_liabilities = -1.0 × 0.02 × 900,000 = -$18,000
      NEV = 100,000 + (-60,000) - (-18,000) = $58,000
    """
    result = await compute_alm(seeded_session, version="current", shocks_bps=(200,))

    assert len(result.shocked) == 1
    up200 = result.shocked[0]
    assert up200.shock_bps == 200
    assert up200.net_interest_income_12mo == Decimal("43000.00")
    assert up200.net_economic_value == Decimal("58000.00")
    assert up200.ear_pct_vs_base == Decimal("4.88")


@pytest.mark.asyncio
async def test_alm_down_100_bps(seeded_session: AsyncSession) -> None:
    """
    -100 bps shock:
      asset yield = 5.00% - 1.00% = 4.00%
      liability cost = 1.00% - 1.00% = 0.00%
      NII = (1,000,000 × 0.04) - (900,000 × 0.00) = 40,000 - 0 = $40,000

    NEV under -100 bps:
      Δrate = -0.01
      ΔV_assets = -3.0 × -0.01 × 1,000,000 = +$30,000
      ΔV_liabilities = -1.0 × -0.01 × 900,000 = +$9,000
      NEV = 100,000 + 30,000 - 9,000 = $121,000
    """
    result = await compute_alm(seeded_session, version="current", shocks_bps=(-100,))

    down100 = result.shocked[0]
    assert down100.shock_bps == -100
    assert down100.net_interest_income_12mo == Decimal("40000.00")
    assert down100.net_economic_value == Decimal("121000.00")


@pytest.mark.asyncio
async def test_alm_default_scenario_set_excludes_zero(seeded_session: AsyncSession) -> None:
    """The default scenario set covers ±100, ±200, ±300; the base case is separate."""
    result = await compute_alm(seeded_session, version="current")
    shocks = sorted(s.shock_bps for s in result.shocked)
    assert shocks == [-300, -200, -100, 100, 200, 300]
