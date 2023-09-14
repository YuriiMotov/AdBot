from dataclasses import dataclass
import pytest
import random
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram_dialog.test_tools import BotClient, MockMessageManager
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker

from adbot.domain import models
from adbot.domain.services import AdBotServices
from adbot.presentation.telegram.tg_bot import TGBot


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


@dataclass
class Env():
    tg_bot: Optional[TGBot] = None
    ad_bot_srv: Optional[AdBotServices] = None
    message_manager: Optional[MockMessageManager] = None
    client: Optional[BotClient] = None
    client_admin: Optional[BotClient] = None
    admin_id: int = 123


@pytest.fixture
def env(in_memory_adbot_srv: AdBotServices) -> Env:

    class TestableTgBotPresentation(TGBot):
        def __init__(
            self, ad_bot_srv: AdBotServices, bot_token: str, redis_db: int,
            admin_id: int, message_manager=None
        ) -> None:
            super().__init__(
                ad_bot_srv, bot_token, redis_db, admin_id, message_manager
            )
            self._send_bot_cmd = AsyncMock()
            self._dp.start_polling = AsyncMock()
            self._dp.stop_polling = AsyncMock()

        def _create_bot(self, bot_token: str):
            return AsyncMock(Bot)
        
        def _create_dp(self: TGBot, redis_db: int):
            return Dispatcher(ad_bot_srv=self._ad_bot_srv)

    e = Env()
    e.ad_bot_srv = in_memory_adbot_srv
    e.message_manager = MockMessageManager()
    e.tg_bot = TestableTgBotPresentation(
        in_memory_adbot_srv, '', 0, e.admin_id, e.message_manager
    )

    tg_user_id = random.randint(e.admin_id, e.admin_id * 10)
    e.client = BotClient(e.tg_bot._dp, tg_user_id, tg_user_id)
    e.client_admin = BotClient(e.tg_bot._dp, e.admin_id, e.admin_id)

    with patch('aiogram.types.Message.delete', new=AsyncMock()):
        with patch('aiogram.types.Message.answer', new=AsyncMock()):
            yield e 


# ==============================================================================================
# helpers

def mock_method_raise_SQLAlchemyError(*arg, **kwarg):
    raise SQLAlchemyError()


def brake_sessionmaker(db_pool: sessionmaker):
    def broken_session_maker():
        session = db_pool()
        session.commit = mock_method_raise_SQLAlchemyError
        session.scalar = mock_method_raise_SQLAlchemyError
        session.scalars = mock_method_raise_SQLAlchemyError
        session.execute = mock_method_raise_SQLAlchemyError
        return session

    return broken_session_maker