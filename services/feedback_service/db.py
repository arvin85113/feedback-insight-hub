import os
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


BASE_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATABASE_URL = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"

DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
