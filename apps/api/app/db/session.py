from collections.abc import Callable, Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

settings = get_settings()

engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

_session_factory: Callable[[], Session] = SessionLocal


def set_session_factory(factory: Callable[[], Session] | None) -> None:
    global _session_factory
    _session_factory = factory if factory is not None else SessionLocal


def create_session() -> Session:
    return _session_factory()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()