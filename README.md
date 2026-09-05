# Yellow-loan-application

A loan application flow for financing a phone: capture biographical
details, income with proof of income, and a phone choice with daily
pricing.

## Stack

- **Backend:** FastAPI + SQLAlchemy (Python 3.13, works on 3.10+)
- **Database:** SQLite
- **Frontend:** Vue 3 (loaded from CDN) + plain CSS, served by FastAPI

## Running it


Requires Python 3.10+.

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python -m backend.seed
    uvicorn backend.main:app --reload

Open http://localhost:8000 for the app, or http://localhost:8000/docs
for the interactive API documentation.

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/phones` | Catalogue with calculated finance terms. Optional `?monthly_income=` shows only phones where income exceeds 10x the monthly payment. |
| POST | `/api/applications` | Create an application. `multipart/form-data`: form fields plus the proof-of-income file. |
| GET | `/api/applications` | All applications, newest first. |
| GET | `/api/applications/{id}/document` | Download the stored proof of income. |

### Validation rules

Every rule below is enforced server-side. The frontend mirrors them for
immediate feedback, but the backend is the control — the frontend can be
bypassed entirely.

- **ID number:** exactly 13 digits, a valid embedded date, citizenship
  digit of 0 or 1, and a correct Luhn check digit.
- **Birthday** must match the date encoded in the ID number.
- **Age** 18-65 inclusive, calculated from the ID's date of birth.
- **ID numbers are unique.** Enforced by a UNIQUE constraint rather than
  a pre-insert check, so two simultaneous requests cannot both succeed.
- **Proof of income** is required: PDF, JPG or PNG, maximum 5 MB.

Status codes: `201` created, `409` duplicate ID, `413` file too large,
`415` unsupported file type, `422` validation failure, `404` not found.
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
- **Upload content types are self-declared.** The allowlist checks the
  `Content-Type` the browser sends, which a determined caller can spoof.
  Verifying magic bytes and serving uploads from a separate domain would
  be the production fix.

## What I'd do next

- **Risk scoring** would need pricing to move out of `phones` into a
  `phone_pricing(phone_id, risk_group, deposit_percent, interest_rate)`
  table, since a phone would then have three sets of terms.
- Affordability filtering on `GET /api/phones`.
- Authentication, and an admin view for reviewing applications.