"""Database engine and session dependency."""

from collections.abc import Generator

from sqlalchemy import Engine
from sqlmodel import Session, create_engine

from app.core.config import settings

engine: Engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"connect_timeout": 3},
    pool_pre_ping=True,  # a dropped connection should not surface as a 500
    pool_size=5,
    max_overflow=10,
    echo=False,
)


def get_session() -> Generator[Session | None, None, None]:
    try:
        with Session(engine) as session:
            yield session
    except Exception:
        yield None
