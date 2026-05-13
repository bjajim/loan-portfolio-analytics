"""ORM models for the loan portfolio."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class LoanSegment(StrEnum):
    AUTO_NEW = "auto_new"
    AUTO_USED = "auto_used"
    UNSECURED = "unsecured"
    REAL_ESTATE = "real_estate"
    CREDIT_CARD = "credit_card"


class LoanStatus(StrEnum):
    CURRENT = "current"
    DELINQUENT_30 = "delinquent_30"
    DELINQUENT_60 = "delinquent_60"
    DELINQUENT_90 = "delinquent_90"
    CHARGED_OFF = "charged_off"
    PAID_OFF = "paid_off"


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(primary_key=True)
    member_id: Mapped[str] = mapped_column(String(32), index=True)
    segment: Mapped[LoanSegment] = mapped_column(String(32), index=True)
    status: Mapped[LoanStatus] = mapped_column(String(32), index=True, default=LoanStatus.CURRENT)
    original_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    current_balance: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4))  # e.g. 0.0625
    term_months: Mapped[int] = mapped_column()
    origination_date: Mapped[date] = mapped_column(Date)
    maturity_date: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class CECLAssumption(Base):
    """Lifetime loss-rate assumption per segment, versioned."""

    __tablename__ = "cecl_assumptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(32), index=True)
    segment: Mapped[LoanSegment] = mapped_column(String(32))
    lifetime_loss_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4))  # e.g. 0.0125 = 1.25%
    effective_date: Mapped[date] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RateAssumption(Base):
    """Base-case rate environment for ALM modeling."""

    __tablename__ = "rate_assumptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(32), index=True)
    asset_yield_base: Mapped[Decimal] = mapped_column(Numeric(6, 4))   # e.g. 0.0550
    liability_cost_base: Mapped[Decimal] = mapped_column(Numeric(6, 4))  # e.g. 0.0125
    total_assets: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    asset_duration_years: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    liability_duration_years: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    effective_date: Mapped[date] = mapped_column(Date)
