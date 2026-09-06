# Yellow — Phone Finance Application

A mobile-first application flow for financing a phone with Yellow: capture
biographical details, income with supporting proof, and a phone choice priced
over 360 daily payments.

Built as a take-home project within a five-hour budget.

## Stack

- **Backend** — FastAPI + SQLAlchemy 2.0, Python 3.13 (requires 3.10+)
- **Database** — SQLite
- **Frontend** — Vue 3 loaded from a CDN, plain CSS, served by FastAPI
- **Tests** — pytest

There is no build step. `pip install` and one command runs the whole thing.

## Running it

    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    python -m backend.seed
    uvicorn backend.main:app --reload

Open <http://localhost:8000> for the application, or
<http://localhost:8000/docs> for the interactive API documentation.

Run the tests with:

    pytest

## Project structure

    backend/
      main.py         API endpoints and file handling
      models.py       SQLAlchemy tables
      schemas.py      Pydantic request/response models
      validators.py   SA ID and age validation
      pricing.py      Loan calculations
      database.py     Engine and session
      seed.py         Phone catalogue
    frontend/
      index.html      Four-step form
      app.js          Vue application and mirrored validation
      styles.css      Mobile-first styling
    tests/
    uploads/          Stored proof-of-income documents (not committed)

## The flow

Four steps rather than one long page. On a phone, a single scrolling form with
eleven fields is intimidating and hard to correct; short steps let each screen
ask one thing and validate before moving on.

1. **Who you are** — name, SA ID number, date of birth
2. **What you earn** — monthly income and a proof-of-income document
3. **Choose a phone** — filtered to what the applicant can afford, priced per day
4. **Check and submit** — full quote breakdown, then submit

## Data model

**phones** — the catalogue. Stores only the three pricing *inputs*:
`cash_price`, `deposit_percent`, `interest_rate`.

**applications** — one row per applicant, with a foreign key to the chosen
phone, the stored document's metadata, and a snapshot of the terms quoted at
submission. `id_number` carries a UNIQUE constraint.

## Pricing

Given a cash price, a deposit percentage and an annual interest rate:

    deposit       = cashPrice x depositPercent
    loanPrincipal = cashPrice x (1 - depositPercent)
    loanAmount    = loanPrincipal x (1 + interestRate)
    dailyPrice    = loanAmount / 360

Worked example — R12 000 at a 15% deposit and 28% interest:

| Step | Result |
|---|---|
| Deposit payable today | R1 800.00 |
| Loan principal | R10 200.00 |
| Total repayable | R13 056.00 |
| **Daily price** | **R36.27** |

All arithmetic runs at full `Decimal` precision and is rounded to cents once,
at the end. Rounding the daily price first and multiplying by 30 would give a
monthly figure of R1 088.10 instead of the correct R1 088.00.

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/phones` | Catalogue with calculated finance terms. Optional `?monthly_income=` returns only phones where income exceeds 10x the monthly payment. |
| `POST` | `/api/applications` | Create an application. `multipart/form-data`: form fields plus the proof-of-income file. |
| `GET` | `/api/applications` | All applications, newest first. |
| `GET` | `/api/applications/{id}/document` | Download the stored proof of income. |

Status codes: `201` created, `409` duplicate ID, `413` file too large,
`415` unsupported file type, `422` validation failure, `404` not found.

## Validation

Every rule is enforced server-side. The frontend mirrors them for immediate
feedback, but the backend is the control — the frontend can be bypassed with a
single `curl` command, and this was tested directly.

- **ID number** — exactly 13 digits, a valid embedded date, a citizenship digit
  of 0 or 1, and a correct Luhn check digit.
- **Date of birth** must match the date encoded in the ID number.
- **Age** 18–65 inclusive.
- **ID numbers are unique** — enforced by a UNIQUE constraint, not a pre-insert
  check, so two simultaneous requests cannot both succeed.
- **Proof of income** required: PDF, JPG or PNG, maximum 5 MB.

### Anatomy of an SA ID number

| Digits | Meaning | Validated |
|---|---|---|
| 1–6 | `YYMMDD` | Must be a real date. The century is ambiguous, so the 2000s are tried first and the 1900s used if that date is in the future. Cross-checked against the stated birthday. |
| 7–10 | Sequence | No |
| 11 | Citizenship | Must be 0 or 1 |
| 12 | Legacy classification digit, unused since 1994 | No |
| 13 | Luhn check digit | Yes |

## Tests

`pytest` covers the two modules where a bug would be silent — a wrong check
digit or a rounding error doesn't announce itself the way a broken endpoint
does. The suite tests the Luhn algorithm against known values, every ID
rejection path, the 18 and 65 age boundaries in both directions, the pricing
calculation against a hand-worked example, and the rounding and `Decimal`
conversion decisions.

Age tests are pinned to a fixed reference date, so "18 years old" doesn't
change meaning as the calendar moves.

## Decisions and trade-offs

**Derived pricing is not stored.** Loan principal, loan amount and daily price
are fully determined by the three inputs, so storing them would let a stored
value drift from its own inputs. They're computed on read.

**Quoted terms are snapshotted onto the application.** This is not a
contradiction of the above: the phone's current price is a fact about the
catalogue, while the terms someone applied under are a historical record. If a
phone is repriced, existing applications must still reflect what was agreed.

**ID numbers are stored as strings.** SA ID numbers can begin with a zero,
which an integer column would silently discard.

**Rates are stored as decimal fractions** (0.28, not 28) so the formulas apply
directly. Conversion to a percentage happens only at display.

**Uploaded files are stored under a generated UUID**, never the user's own
filename, which is attacker-controlled input. The original name is kept
separately as a display label and used when serving the file back.

**SQLite over Postgres.** Zero setup cost inside a five-hour budget. Because
SQLAlchemy sits in between, moving to Postgres is a connection-string change
plus a migration tool.

**Vue from a CDN, no build step.** Avoids spending an hour of a five-hour
budget on tooling, and keeps the whole project runnable with `pip install` and
one command. A production app would use a proper build.

**No web fonts.** The system font stack renders instantly with no network
request, which matters more on mobile data than matching an exact typeface.

## Known limitations

- **Money precision.** SQLite has no native decimal type, so SQLAlchemy
  converts `Numeric` values via floating point. Exact in Postgres; the fully
  robust approach either way is storing integer cents.
- **Document storage.** Files are written to local disk with the path recorded
  on the application row. That disk is wiped on redeploy and isn't shared
  between server instances — in production this becomes object storage with the
  key in the database.
- **Upload content types are self-declared.** The allowlist checks the
  `Content-Type` the browser sends, which a determined caller can spoof.
  Verifying magic bytes and serving uploads from a separate domain would be the
  production fix.
- **Validation logic is duplicated** between Python and JavaScript, so the two
  can drift. A larger system would generate one from the other or share a
  schema.
- **No migrations.** Schema changes require deleting `yellow.db` and recreating
  it. Alembic would handle this properly.
- **No authentication.** Anyone can list applications and download documents,
  which is fine for a demo and not for anything real.

## What I'd do next

- **Risk scoring** would move pricing out of `phones` into a
  `phone_pricing(phone_id, risk_group, deposit_percent, interest_rate)` table,
  since a phone would then carry three sets of terms.
- Integration tests over the endpoints with FastAPI's `TestClient`.
- Object storage for documents, and Alembic for migrations.
- Authentication plus an admin view for reviewing applications.
- Mock payment checkout, tracking applications started versus completed.

## Scope

Built to the five-hour limit. The affordability filter is implemented; risk
scoring and mock payment were deliberately left out in favour of getting the
core flow, both validation layers, document storage and tests genuinely
finished rather than several features half-done.