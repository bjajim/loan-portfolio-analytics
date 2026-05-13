"""Pydantic schemas for API request/response models."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.loan import LoanSegment, LoanStatus


class LoanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    member_id: str
    segment: LoanSegment
    status: LoanStatus
    original_balance: Decimal
    current_balance: Decimal
    interest_rate: Decimal
    term_months: int
    origination_date: date
    maturity_date: date


class PortfolioSummary(BaseModel):
    total_loans: int
    total_balance: Decimal
    by_segment: dict[str, Decimal]
    by_status: dict[str, int]
    delinquency_rate: Decimal = Field(description="Share of balance 30+ days delinquent")
    weighted_avg_rate: Decimal


class CECLSegmentResult(BaseModel):
    segment: LoanSegment
    exposure: Decimal
    loss_rate: Decimal
    allowance: Decimal


class CECLResult(BaseModel):
    assumption_version: str
    total_exposure: Decimal
    total_allowance: Decimal
    coverage_ratio: Decimal = Field(description="allowance / exposure")
    by_segment: list[CECLSegmentResult]


class ALMScenarioResult(BaseModel):
    shock_bps: int
    asset_yield: Decimal
    liability_cost: Decimal
    net_interest_income_12mo: Decimal
    net_economic_value: Decimal
    ear_pct_vs_base: Decimal = Field(description="EaR as % vs base case (negative = loss)")
    nev_pct_vs_base: Decimal


class ALMResult(BaseModel):
    assumption_version: str
    base_case: ALMScenarioResult
    shocked: list[ALMScenarioResult]
