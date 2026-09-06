"""FastAPI application: phone catalogue and loan applications."""

import uuid
from decimal import Decimal
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .database import Base, engine, get_db
from .models import Application, Phone
from .pricing import is_affordable, price_phone
from .schemas import ApplicationCreate, ApplicationOut, PhoneOut

BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"
FRONTEND_DIR = BASE_DIR / "frontend"

MAX_UPLOAD_BYTES = 5 * 1024 * 1024          # 5 MB
ALLOWED_TYPES = {
    "application/pdf": ".pdf",
    "image/jpeg": ".jpg",
    "image/png": ".png",
}

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Yellow Loan Application",
    description="Apply to finance a phone over 360 daily payments.",
    version="1.0.0",
)


def _first_message(exc: ValidationError) -> str:
    """Pull one readable sentence out of a Pydantic error."""
    message = exc.errors()[0]["msg"]
    return message.removeprefix("Value error, ")


# --------------------------------------------------------------- phones

@app.get("/api/phones", response_model=list[PhoneOut])
def list_phones(
    monthly_income: Decimal | None = None,
    db: Session = Depends(get_db),
):
    """The catalogue with finance terms.

    Pass ?monthly_income= to show only phones the applicant can afford
    (monthly income must exceed 10x the monthly payment).
    """
    phones = (
        db.query(Phone)
        .filter(Phone.is_active.is_(True))
        .order_by(Phone.cash_price)
        .all()
    )

    results = []
    for phone in phones:
        pricing = price_phone(
            phone.cash_price, phone.deposit_percent, phone.interest_rate
        )
        if monthly_income is not None and not is_affordable(
            monthly_income, pricing.monthly_price
        ):
            continue
        results.append(PhoneOut.build(phone, pricing))
    return results


# --------------------------------------------------------- applications

@app.post("/api/applications", response_model=ApplicationOut, status_code=201)
def create_application(
    full_name: str = Form(...),
    id_number: str = Form(...),
    date_of_birth: str = Form(...),
    monthly_income: str = Form(...),
    phone_id: int = Form(...),
    document: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Create an application. Multipart: text fields plus the proof document."""

    # 1. Text fields through Pydantic (ID validity, birthday match, age).
    try:
        data = ApplicationCreate(
            full_name=full_name,
            id_number=id_number,
            date_of_birth=date_of_birth,
            monthly_income=monthly_income,
            phone_id=phone_id,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=_first_message(exc))

    # 2. The chosen phone must exist and still be on sale.
    phone = db.get(Phone, data.phone_id)
    if phone is None or not phone.is_active:
        raise HTTPException(status_code=404, detail="That phone is not available.")

    # 3. Friendly duplicate check. The UNIQUE constraint is the real guarantee.
    if db.query(Application).filter_by(id_number=data.id_number).first():
        raise HTTPException(
            status_code=409,
            detail="An application already exists for this ID number.",
        )

    # 4. Validate the document, then write it under a name we generate.
    extension = ALLOWED_TYPES.get(document.content_type)
    if extension is None:
        raise HTTPException(
            status_code=415, detail="Upload a PDF, JPG or PNG."
        )

    contents = document.file.read()
    if not contents:
        raise HTTPException(status_code=422, detail="The uploaded file is empty.")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413, detail="Proof of income must be 5 MB or smaller."
        )

    UPLOAD_DIR.mkdir(exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{extension}"
    (UPLOAD_DIR / stored_name).write_bytes(contents)

    # 5. Insert, snapshotting the terms as quoted right now.
    application = Application(
        full_name=data.full_name,
        id_number=data.id_number,
        date_of_birth=data.date_of_birth,
        monthly_income=data.monthly_income,
        document_path=stored_name,
        document_filename=document.filename or stored_name,
        document_content_type=document.content_type,
        document_size=len(contents),
        phone_id=phone.id,
        quoted_cash_price=phone.cash_price,
        quoted_deposit_percent=phone.deposit_percent,
        quoted_interest_rate=phone.interest_rate,
    )
    db.add(application)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        (UPLOAD_DIR / stored_name).unlink(missing_ok=True)
        raise HTTPException(
            status_code=409,
            detail="An application already exists for this ID number.",
        )
    except Exception:
        # Any other failure: don't leave an orphaned file behind.
        db.rollback()
        (UPLOAD_DIR / stored_name).unlink(missing_ok=True)
        raise

    db.refresh(application)
    return application


@app.get("/api/applications", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    """All applications, newest first."""
    return (
        db.query(Application).order_by(Application.created_at.desc()).all()
    )


@app.get("/api/applications/{application_id}/document")
def get_document(application_id: int, db: Session = Depends(get_db)):
    """Serve the stored proof of income back under its original filename."""
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found.")

    path = UPLOAD_DIR / application.document_path
    if not path.exists():
        raise HTTPException(status_code=404, detail="Stored document is missing.")

    return FileResponse(
        path,
        media_type=application.document_content_type,
        filename=application.document_filename,
    )


# ------------------------------------------------------------- frontend
# MUST be last: mounting at "/" catches everything not matched above.

if FRONTEND_DIR.exists():
    app.mount(
        "/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend"
    )