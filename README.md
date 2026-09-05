# Yellow-loan-application

A loan application flow for financing a phone: capture biographical
details, income with proof of income, and a phone choice with daily
pricing.

## Stack

- **Backend:** FastAPI + SQLAlchemy (Python 3.13, works on 3.10+)
- **Database:** SQLite
- **Frontend:** Vue 3 (loaded from CDN) + plain CSS, served by FastAPI

## Running it

(to fill in)

## Data model

**phones** — the catalogue. Stores only the three pricing *inputs*:
`cash_price`, `deposit_percent`, `interest_rate`.

**applications** — one row per applicant. `id_number` carries a UNIQUE
constraint. Holds a snapshot of the terms quoted at submission.

## Decisions and trade-offs

**Derived pricing is not stored.** Loan principal, loan amount and daily
price are all determined by the three inputs above, so storing them
would allow the stored value to drift from its own inputs. They're
computed on read in `pricing.py`.

**Quoted terms are snapshotted onto the application.** This looks like a
contradiction of the above but isn't: the phone's current price is a
fact about the catalogue, while the terms someone applied under are a
historical record. If Yellow reprices a phone, existing applications
must still reflect what was agreed.

**ID numbers are stored as strings.** SA ID numbers can begin with a
zero (anyone born in 2000-2009), which an integer column would silently
discard.

**Rates are stored as decimal fractions** (0.28, not 28) so the pricing
formulas apply directly. Conversion to a percentage happens only at
display.

**Uniqueness is enforced by the database, not by application code.** The
Python check exists to produce a friendly error message; the UNIQUE
constraint is what actually guarantees it. A pre-insert check alone
would race between two simultaneous requests.

**SQLite over Postgres.** Zero setup cost inside a 5-hour budget. Because
SQLAlchemy sits in between, moving to Postgres is a connection-string
change plus a real migration tool.

## Known limitations

- **Money precision.** SQLite has no native decimal type, so SQLAlchemy
  converts `Numeric` via floating point. Exact in Postgres; the fully
  robust approach either way is storing integer cents.
- **Document storage.** Uploaded files are written to local disk with the
  path recorded on the application row. That disk is wiped on redeploy
  and isn't shared between server instances — in production this becomes
  object storage with the key in the database.
- **No migrations.** Schema changes require deleting `yellow.db` and
  recreating it. Alembic would handle this properly.

## What I'd do next

- **Risk scoring** would need pricing to move out of `phones` into a
  `phone_pricing(phone_id, risk_group, deposit_percent, interest_rate)`
  table, since a phone would then have three sets of terms.
- Affordability filtering on `GET /api/phones`.
- Authentication, and an admin view for reviewing applications.