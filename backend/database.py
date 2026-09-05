from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# Three slashes = a path relative to wherever you run the app from.
DATABASE_URL = "sqlite:///./yellow.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """All table classes inherit from this."""
    pass


def get_db():
    """Hand a database session to one request, then always close it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()