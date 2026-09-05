"""Validation for South African ID numbers and applicant age."""

from datetime import date

MIN_AGE = 18
MAX_AGE = 65


class IDValidationError(ValueError):
    """Raised when an ID number or applicant age fails validation."""


def luhn_check_digit(first_twelve: str) -> int:
    """Compute the 13th digit of an SA ID number from the first 12."""
    total = 0
    for position, char in enumerate(reversed(first_twelve)):
        digit = int(char)
        if position % 2 == 0:      # every second digit, counting from the right
            digit *= 2
            if digit > 9:
                digit -= 9         # identical to summing the two digits
        total += digit
    return (10 - (total % 10)) % 10


def _date_of_birth(yymmdd: str) -> date:
    """Turn the first six digits into a real date, resolving the century."""
    year_2, month, day = int(yymmdd[:2]), int(yymmdd[2:4]), int(yymmdd[4:6])
    today = date.today()

    # Prefer the 2000s; fall back to the 1900s if that would be in the future.
    for century in (2000, 1900):
        try:
            candidate = date(century + year_2, month, day)
        except ValueError:
            continue               # e.g. 31 February, or month 13
        if candidate <= today:
            return candidate

    raise IDValidationError("ID number contains an invalid date of birth.")


def parse_sa_id(id_number: str) -> date:
    """Validate an SA ID number and return the date of birth it encodes.

    Raises IDValidationError with a user-facing message on any failure.
    """
    if not id_number:
        raise IDValidationError("ID number is required.")

    cleaned = id_number.strip().replace(" ", "")

    if not cleaned.isdigit():
        raise IDValidationError("ID number must contain digits only.")
    if len(cleaned) != 13:
        raise IDValidationError("ID number must be exactly 13 digits.")

    date_of_birth = _date_of_birth(cleaned[:6])

    if cleaned[10] not in ("0", "1"):
        raise IDValidationError("ID number has an invalid citizenship digit.")

    if int(cleaned[12]) != luhn_check_digit(cleaned[:12]):
        raise IDValidationError("ID number is not valid. Please check for typos.")

    return date_of_birth


def calculate_age(date_of_birth: date, on: date | None = None) -> int:
    """Age in completed years, as at `on` (default today)."""
    on = on or date.today()
    had_birthday = (on.month, on.day) >= (date_of_birth.month, date_of_birth.day)
    return on.year - date_of_birth.year - (0 if had_birthday else 1)


def validate_age(date_of_birth: date, on: date | None = None) -> int:
    """Enforce the 18-65 inclusive rule. Returns the age."""
    age = calculate_age(date_of_birth, on)
    if age < MIN_AGE:
        raise IDValidationError(
            f"Applicants must be at least {MIN_AGE} years old."
        )
    if age > MAX_AGE:
        raise IDValidationError(
            f"Applicants must be {MAX_AGE} years old or younger."
        )
    return age


def validate_identity(id_number: str, stated_date_of_birth: date) -> date:
    """Full check: valid ID, birthday matches it, age within range."""
    date_of_birth = parse_sa_id(id_number)

    if stated_date_of_birth != date_of_birth:
        raise IDValidationError(
            "The date of birth does not match the one in your ID number."
        )

    validate_age(date_of_birth)
    return date_of_birth