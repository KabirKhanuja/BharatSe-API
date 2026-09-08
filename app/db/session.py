"""Database engine and session dependency."""

from collections.abc import Generator

from sqlalchemy import Engine
from sqlmodel import Session, create_engine

from app.core.config import settings

engine: Engine = create_engine(
    settings.DATABASE_URL,
    # 3 seconds was too tight and it cost us a deploy. A cold connection to the
    # Supabase session pooler takes about 2.5s from a laptop on good wifi, and
    # more from a server in another region once TLS is included, so it timed
    # out every time and surfaced as "database unreachable" with no clue why.
    #
    # This is a ceiling, not a target: a healthy connection still returns in
    # milliseconds. It only decides how long we wait before giving up.
    connect_args={"connect_timeout": 15},
    pool_pre_ping=True,  # a dropped connection should not surface as a 500
    pool_size=5,
    max_overflow=10,
    echo=False,
)


def get_session() -> Generator[Session, None, None]:
    """Hand a session to the route and clean it up afterwards.

    Deliberately does NOT swallow exceptions. FastAPI throws whatever the route
    raised back in at the yield point, so catching it here and yielding a second
    time makes Python raise "generator didn\'t stop after throw()" and loses the
    real error. Every 401 became a RuntimeError that way.

    Graceful degradation when the database is unreachable is handled by the
    OperationalError handler in main.py, which turns it into a 503 instead of a
    500. That belongs there, not here.
    """
    with Session(engine) as session:
        yield session
