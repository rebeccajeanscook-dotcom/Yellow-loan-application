"""Tests for SA ID validation and the age rule."""

from datetime import date

import pytest

from backend.validators import (
    IDValidationError,
    calculate_age,
    luhn_check_digit,
    parse_sa_id,
    validate_age,
    validate_identity,
)

# Fixed reference date so age tests don't change meaning tomorrow.
TODAY = date(2026, 9, 6)


def test_luhn_check_digit_matches_a_known_value():
    assert luhn_check_digit("800101500908") == 7


@pytest.mark.parametrize("id_number, expected", [
    ("8001015009087", date(1980, 1, 1)),
    ("9106155009083", date(1991, 6, 15)),
    ("9304225009080", date(1993, 4, 22)),
])
def test_valid_ids_return_their_date_of_birth(id_number, expected):
    assert parse_sa_id(id_number) == expected


@pytest.mark.parametrize("id_number", [
    "8001015009088",    # wrong check digit
    "800101500908",     # 12 digits
    "80010150090871",   # 14 digits
    "80010150090a7",    # contains a letter
    "8001015009287",    # citizenship digit is 2
    "8013015009087",    # month 13
    "",                 # empty
])
def test_invalid_ids_are_rejected(id_number):
    with pytest.raises(IDValidationError):
        parse_sa_id(id_number)


def test_spaces_are_tolerated():
    assert parse_sa_id("800101 5009 087") == date(1980, 1, 1)


@pytest.mark.parametrize("date_of_birth, expected", [
    (date(2008, 9, 6), 18),     # birthday is today
    (date(2008, 9, 7), 17),     # birthday is tomorrow
    (date(1961, 9, 6), 65),
    (date(1960, 9, 6), 66),
])
def test_age_is_counted_in_completed_years(date_of_birth, expected):
    assert calculate_age(date_of_birth, on=TODAY) == expected


def test_age_limits_are_inclusive_at_both_ends():
    assert validate_age(date(2008, 9, 6), on=TODAY) == 18
    assert validate_age(date(1961, 9, 6), on=TODAY) == 65


@pytest.mark.parametrize("date_of_birth", [
    date(2008, 9, 7),           # 17
    date(1960, 9, 6),           # 66
])
def test_ages_outside_the_range_are_rejected(date_of_birth):
    with pytest.raises(IDValidationError):
        validate_age(date_of_birth, on=TODAY)


def test_stated_birthday_must_match_the_id():
    with pytest.raises(IDValidationError, match="does not match"):
        validate_identity("9304225009080", date(1993, 4, 23))


def test_matching_birthday_is_accepted():
    assert validate_identity("9304225009080", date(1993, 4, 22)) \
        == date(1993, 4, 22)