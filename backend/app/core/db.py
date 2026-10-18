from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import Settings


class Base(DeclarativeBase):
    pass


def make_session_factory(settings: Settings) -> sessionmaker[Session]:
    engine: Engine = create_engine(settings.database_url.get_secret_value(), pool_pre_ping=True)
    return sessionmaker(bind=engine)


def get_db(request: Request) -> Iterator[Session]:
    factory: sessionmaker[Session] = request.app.state.session_factory
    with factory() as session:
        yield session
