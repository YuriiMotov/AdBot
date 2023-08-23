import pytest

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker, Session

from adbot.domain import models
from adbot.domain.services import AdBotServices


@pytest.fixture
def in_memory_adbot_srv():
    engine = create_engine('sqlite:///:memory:', pool_pre_ping=True)
    models.Base.metadata.drop_all(engine)
    models.Base.metadata.create_all(engine)
    db_pool = sessionmaker(bind=engine)
    adbot_srv = AdBotServices(db_pool)
    return adbot_srv


