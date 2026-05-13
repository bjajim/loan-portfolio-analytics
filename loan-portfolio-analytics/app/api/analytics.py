"""Analytics endpoints: portfolio summary, CECL, ALM."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.analytics import ALMResult, CECLResult, PortfolioSummary
from app.services import compute_alm, compute_cecl, portfolio_summary

router = APIRouter()


@router.get("/portfolio/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(
    session: AsyncSession = Depends(get_session),
) -> PortfolioSummary:
    """Portfolio-wide KPIs: balance, segment mix, delinquency, weighted rate."""
    return await portfolio_summary(session)


@router.get("/analytics/cecl", response_model=CECLResult)
async def get_cecl(
    version: str = Query("current", description="Assumption version to use"),
    session: AsyncSession = Depends(get_session),
) -> CECLResult:
    """CECL allowance calculation using the configured methodology."""
    try:
        return await compute_cecl(session, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.get("/analytics/alm", response_model=ALMResult)
async def get_alm(
    version: str = Query("current", description="Rate assumption version"),
    shock_bps: int | None = Query(
        None,
        description="If set, only this single shock is returned (otherwise the full -300..+300 set).",
    ),
    session: AsyncSession = Depends(get_session),
) -> ALMResult:
    """ALM rate-shock simulation: NEV and EaR under parallel rate shifts."""
    try:
        if shock_bps is not None:
            return await compute_alm(session, version, shocks_bps=(shock_bps,))
        return await compute_alm(session, version)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
