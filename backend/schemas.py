"""Pydantic models: the shape of everything entering and leaving the API."""

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .validators import validate_identity


# ---------- outgoing ----------

class PhoneOut(BaseModel):
    """A phone plus its calculated finance terms."""
    id: int
    brand: str
    model: str
    image_url: str | None = None

    cash_price: Decimal
    deposit_percent: Decimal
    interest_rate: Decimal

    deposit: Decimal
    loan_principal: Decimal
    loan_amount: Decimal
    daily_price: Decimal
    monthly_price: Decimal

    @classmethod
    def build(cls, phone, pricing) -> "PhoneOut":
        """Combine a Phone row with the output of price_phone()."""
        return cls(
            id=phone.id,
            brand=phone.brand,
            model=phone.model,
            image_url=phone.image_url,
            cash_price=pricing.cash_price,
            deposit_percent=pricing.deposit_percent,
            interest_rate=pricing.interest_rate,
            deposit=pricing.deposit,
            loan_principal=pricing.loan_principal,
            loan_amount=pricing.loan_amount,
            daily_price=pricing.daily_price,
            monthly_price=pricing.monthly_price,
        )


class ApplicationOut(BaseModel):
    """What we send back after a successful application."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    id_number: str
    date_of_birth: date
    monthly_income: Decimal
    phone_id: int
    document_filename: str
    created_at: datetime

    quoted_cash_price: Decimal
    quoted_deposit_percent: Decimal
    quoted_interest_rate: Decimal


# ---------- incoming ----------

class ApplicationCreate(BaseModel):
    """Everything the applicant submits, apart from the file itself."""

    full_name: str = Field(min_length=2, max_length=120)
    id_number: str = Field(min_length=13, max_length=20)
    date_of_birth: date
    monthly_income: Decimal = Field(gt=0, le=Decimal("10000000"))
    phone_id: int = Field(gt=0)

    @field_validator("full_name")
    @classmethod
    def tidy_name(cls, value: str) -> str:
        # Collapse runs of whitespace: "  Rebecca   Cook " -> "Rebecca Cook"
        return " ".join(value.split())

    @field_validator("id_number")
    @classmethod
    def strip_id(cls, value: str) -> str:
        return value.strip().replace(" ", "")

    @model_validator(mode="after")
    def check_identity(self) -> "ApplicationCreate":
        # Runs after every field is present: validates the ID, confirms the
        # stated birthday matches it, and enforces the 18-65 rule.
        validate_identity(self.id_number, self.date_of_birth)
        return self