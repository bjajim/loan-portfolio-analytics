"""ALM (Asset-Liability Management) interest-rate shock simulation.

Computes Net Economic Value (NEV) and Earnings at Risk (EaR) under parallel
interest-rate shocks. The methodology is simplified relative to what a
regulator would expect on a Call Report (no convexity adjustment, no
prepayment behavior modeling) but appropriate for an internal management
dashboard. Convexity and prepayment layers can be added in the same shape
without changing the API contract.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.loan import RateAssumption
from app.schemas.analytics import ALMResult, ALMScenarioResult

# Standard regulator-style scenario set.
_DEFAULT_SHOCKS_BPS = (-300, -200, -100, 0, 100, 200, 300)


def _bps_to_rate(bps: int) -> Decimal:
    return Decimal(bps) / Decimal("10000")


def _scenario(
    assumption: RateAssumption,
    shock_bps: int,
    base_nii: Decimal,
    base_nev: Decimal,
) -> ALMScenarioResult:
    shock = _bps_to_rate(shock_bps)
    asset_yield = assumption.asset_yield_base + shock
    liability_cost = assumption.liability_cost_base + shock

    # 12-month projected net interest income under shocked rates.
    nii_12mo = (
        assumption.total_assets * asset_yield
        - assumption.total_liabilities * liability_cost
    ).quantize(Decimal("0.01"))

    # NEV approximation via duration: change in equity value ≈
    #   -duration_gap × Δrate × earning_assets
    # Using independent durations for assets vs liabilities.
    equity = assumption.total_assets - assumption.total_liabilities
    dv_assets = -assumption.asset_duration_years * shock * assumption.total_assets
    dv_liabilities = -assumption.liability_duration_years * shock * assumption.total_liabilities
    nev = (equity + dv_assets - dv_liabilities).quantize(Decimal("0.01"))

    ear_pct = (
        ((nii_12mo - base_nii) / base_nii * Decimal("100")).quantize(Decimal("0.01"))
        if base_nii != 0
        else Decimal("0")
    )
    nev_pct = (
        ((nev - base_nev) / base_nev * Decimal("100")).quantize(Decimal("0.01"))
        if base_nev != 0
        else Decimal("0")
    )

    return ALMScenarioResult(
        shock_bps=shock_bps,
        asset_yield=asset_yield.quantize(Decimal("0.0001")),
        liability_cost=liability_cost.quantize(Decimal("0.0001")),
        net_interest_income_12mo=nii_12mo,
        net_economic_value=nev,
        ear_pct_vs_base=ear_pct,
        nev_pct_vs_base=nev_pct,
    )


async def compute_alm(
    session: AsyncSession,
    version: str = "current",
    shocks_bps: tuple[int, ...] = _DEFAULT_SHOCKS_BPS,
) -> ALMResult:
    stmt = select(RateAssumption).where(RateAssumption.version == version)
    assumption = (await session.execute(stmt)).scalar_one_or_none()
    if assumption is None:
        raise ValueError(f"No rate assumptions found for version '{version}'")

    # Compute base case first so all scenarios can express deltas against it.
    base_nii = (
        assumption.total_assets * assumption.asset_yield_base
        - assumption.total_liabilities * assumption.liability_cost_base
    )
    base_nev = assumption.total_assets - assumption.total_liabilities

    base_case = _scenario(assumption, 0, base_nii, base_nev)
    shocked = [
        _scenario(assumption, bps, base_nii, base_nev)
        for bps in shocks_bps
        if bps != 0
    ]

    return ALMResult(
        assumption_version=version,
        base_case=base_case,
        shocked=shocked,
    )
