import pytest

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from adbot.domain import models
from adbot.domain.services import AdBotServices


@pytest.fixture
def in_memory_db_sessionmaker():
    engine = create_engine('sqlite:///:memory:', pool_pre_ping=True)
    models.Base.metadata.drop_all(engine)
    models.Base.metadata.create_all(engine)
    db_pool = sessionmaker(bind=engine)
    return db_pool


@pytest.fixture
def in_memory_adbot_srv(in_memory_db_sessionmaker):
    adbot_srv = AdBotServices(in_memory_db_sessionmaker)
    return adbot_srv


