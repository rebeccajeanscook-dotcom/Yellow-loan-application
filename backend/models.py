from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, func
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Phone(Base):
    """A phone Yellow offers, with the inputs needed to price it."""
    __tablename__ = "phones"

    id: Mapped[int] = mapped_column(primary_key=True)

    brand: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(80))

    # Money. Numeric(10, 2) = up to 8 digits before the decimal, 2 after.
    cash_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))

    # Stored as fractions: 0.1500 = 15%, 0.2800 = 28%.
    deposit_percent: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))

    image_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    applications: Mapped[list["Application"]] = relationship(
        back_populates="phone"
    )

    def __repr__(self) -> str:
        return f"<Phone {self.brand} {self.model} R{self.cash_price}>"


class Application(Base):
    """One person's application for one phone."""
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)

    # --- biographical ---
    full_name: Mapped[str] = mapped_column(String(120))
    # String, never Integer: SA IDs can start with 0.
    id_number: Mapped[str] = mapped_column(String(13), unique=True, index=True)
    date_of_birth: Mapped[date] = mapped_column(Date)

    # --- income ---
    monthly_income: Mapped[Decimal] = mapped_column(Numeric(12, 2))

    # --- proof of income document ---
    document_path: Mapped[str] = mapped_column(String(255))
    document_filename: Mapped[str] = mapped_column(String(255))
    document_content_type: Mapped[str] = mapped_column(String(100))
    document_size: Mapped[int] = mapped_column(Integer)

    # --- phone choice ---
    phone_id: Mapped[int] = mapped_column(ForeignKey("phones.id"))

    # --- terms as quoted at submission (a contract, not a duplicate) ---
    quoted_cash_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    quoted_deposit_percent: Mapped[Decimal] = mapped_column(Numeric(5, 4))
    quoted_interest_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4))

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    phone: Mapped["Phone"] = relationship(back_populates="applications")

    def __repr__(self) -> str:
        return f"<Application {self.id} {self.full_name}>"