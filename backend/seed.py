"""Populate the database with a starting phone catalogue.

Run from the project root:

    python -m backend.seed            # seed if empty
    python -m backend.seed --reset    # wipe phones and re-seed
"""

import sys
from decimal import Decimal

from .database import Base, SessionLocal, engine
from .models import Phone

# Deposit and interest are fractions: 0.15 = 15%.
# Cheaper handsets carry a higher rate and a lower deposit, which is
# roughly how entry-level device finance is priced in practice.
PHONES = [
    {
        "brand": "Hisense", "model": "E20",
        "cash_price": Decimal("1299.00"),
        "deposit_percent": Decimal("0.10"),
        "interest_rate": Decimal("0.36"),
    },
    {
        "brand": "Samsung", "model": "Galaxy A06",
        "cash_price": Decimal("2799.00"),
        "deposit_percent": Decimal("0.12"),
        "interest_rate": Decimal("0.32"),
    },
    {
        "brand": "Xiaomi", "model": "Redmi 14C",
        "cash_price": Decimal("3499.00"),
        "deposit_percent": Decimal("0.15"),
        "interest_rate": Decimal("0.30"),
    },
    {
        "brand": "Samsung", "model": "Galaxy A26 5G",
        "cash_price": Decimal("6499.00"),
        "deposit_percent": Decimal("0.15"),
        "interest_rate": Decimal("0.28"),
    },
    {
        "brand": "Google", "model": "Pixel 9a",
        "cash_price": Decimal("11999.00"),
        "deposit_percent": Decimal("0.20"),
        "interest_rate": Decimal("0.26"),
    },
    {
        "brand": "Apple", "model": "iPhone 16",
        "cash_price": Decimal("19999.00"),
        "deposit_percent": Decimal("0.25"),
        "interest_rate": Decimal("0.24"),
    },
]


def seed(reset: bool = False) -> None:
    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        existing = session.query(Phone).count()

        if existing and not reset:
            print(f"{existing} phones already present — nothing to do.")
            print("Use --reset to wipe and re-seed.")
            return

        if reset:
            deleted = session.query(Phone).delete()
            print(f"Removed {deleted} existing phones.")

        session.add_all(Phone(**data) for data in PHONES)
        session.commit()
        print(f"Seeded {len(PHONES)} phones.")
    finally:
        session.close()


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)