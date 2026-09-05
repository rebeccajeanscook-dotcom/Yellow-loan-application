"""Loan pricing. Pure functions — no database, no request objects."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

LOAN_TERM_DAYS = 360
DAYS_PER_MONTH = 30


@dataclass(frozen=True)
class PhonePricing:
    """Every number needed to display and record a phone's finance terms."""
    cash_price: Decimal
    deposit_percent: Decimal
    interest_rate: Decimal
    deposit: Decimal
    loan_principal: Decimal
    loan_amount: Decimal
    daily_price: Decimal
    monthly_price: Decimal


def _as_decimal(value) -> Decimal:
    """Convert to Decimal via str, so floats don't smuggle in binary error."""
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _to_money(value: Decimal) -> Decimal:
    """Round to cents, half-up (the financial convention, not Python's default)."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def price_phone(cash_price, deposit_percent, interest_rate) -> PhonePricing:
    """Turn a phone's three pricing inputs into its full finance terms.

    deposit_percent and interest_rate are fractions: 0.15 means 15%.
    """
    cash_price = _as_decimal(cash_price)
    deposit_percent = _as_decimal(deposit_percent)
    interest_rate = _as_decimal(interest_rate)

    if cash_price <= 0:
        raise ValueError("Cash price must be greater than zero.")
    if not (0 <= deposit_percent < 1):
        raise ValueError("Deposit percent must be a fraction between 0 and 1.")
    if interest_rate < 0:
        raise ValueError("Interest rate cannot be negative.")

    # Compute the whole chain at full precision; round only at the end.
    deposit = cash_price * deposit_percent
    loan_principal = cash_price * (Decimal(1) - deposit_percent)
    loan_amount = loan_principal * (Decimal(1) + interest_rate)
    daily_price = loan_amount / LOAN_TERM_DAYS
    monthly_price = daily_price * DAYS_PER_MONTH

    return PhonePricing(
        cash_price=_to_money(cash_price),
        deposit_percent=deposit_percent,
        interest_rate=interest_rate,
        deposit=_to_money(deposit),
        loan_principal=_to_money(loan_principal),
        loan_amount=_to_money(loan_amount),
        daily_price=_to_money(daily_price),
        monthly_price=_to_money(monthly_price),
    )


def is_affordable(monthly_income, monthly_price, multiple: int = 10) -> bool:
    """True when monthly income exceeds `multiple` times the monthly payment."""
    return _as_decimal(monthly_income) > _as_decimal(monthly_price) * multiple