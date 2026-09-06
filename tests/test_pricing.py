"""Tests for the loan pricing calculation."""

from decimal import Decimal

import pytest

from backend.pricing import is_affordable, price_phone


def test_worked_example_matches_the_hand_calculation():
    """R12 000 phone, 15% deposit, 28% interest."""
    pricing = price_phone(12000, "0.15", "0.28")

    assert pricing.deposit == Decimal("1800.00")
    assert pricing.loan_principal == Decimal("10200.00")
    assert pricing.loan_amount == Decimal("13056.00")
    assert pricing.daily_price == Decimal("36.27")


def test_monthly_price_is_not_compounded_from_a_rounded_daily():
    """36.27 x 30 would give 1088.10. Rounding once, at the end, gives 1088.00."""
    assert price_phone(12000, "0.15", "0.28").monthly_price == Decimal("1088.00")


def test_float_inputs_do_not_leak_binary_rounding_error():
    """Decimal(0.15) is not 0.15; converting via str() is what makes this exact."""
    assert price_phone(12000, 0.15, 0.28).deposit == Decimal("1800.00")


def test_zero_deposit_leaves_the_whole_price_as_principal():
    pricing = price_phone(1000, 0, 0)
    assert pricing.loan_principal == Decimal("1000.00")
    assert pricing.loan_amount == Decimal("1000.00")


@pytest.mark.parametrize("cash_price, deposit, interest", [
    (0, "0.15", "0.28"),        # free phone
    (-100, "0.15", "0.28"),     # negative price
    (12000, "1.0", "0.28"),     # 100% deposit is not a loan
    (12000, "-0.1", "0.28"),    # negative deposit
    (12000, "0.15", "-0.5"),    # negative interest
])
def test_nonsense_inputs_are_rejected(cash_price, deposit, interest):
    with pytest.raises(ValueError):
        price_phone(cash_price, deposit, interest)


def test_affordability_requires_income_above_ten_times_the_payment():
    monthly = Decimal("1088.00")
    assert is_affordable(Decimal("10880.01"), monthly) is True
    assert is_affordable(Decimal("10880.00"), monthly) is False   # strictly greater