import asyncio
from dataclasses import dataclass
import pytest
import pytest_asyncio
import random
from typing import Optional
from unittest.mock import AsyncMock, patch

from aiogram import Bot, Dispatcher
from aiogram.types import Message
from aiogram_dialog.test_tools import BotClient, MockMessageManager
from telethon import TelegramClient
from telethon.tl.types import User
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import async_sessionmaker,create_async_engine

from adbot.domain import models
from adbot.app.app import AdBotApp
from adbot.app.config_reader import config
from adbot.domain.services import AdBotServices
from adbot.presentation.telegram.tg_bot import TGBot
from adbot.presentation.telegram.filters import SenderId


async def _sessionmaker(url: str) -> async_sessionmaker:
    engine = create_async_engine(
        url, pool_pre_ping=True,
    )

    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.drop_all)
        await conn.run_sync(models.Base.metadata.create_all)

    db_pool = async_sessionmaker(
        bind=engine, expire_on_commit=False
    )
    return db_pool


async def _in_memory_db_sessionmaker() -> async_sessionmaker:
    return await _sessionmaker('sqlite+aiosqlite:///:memory:')

@pytest_asyncio.fixture    
async def file_db_sessionmaker() -> async_sessionmaker:
    return await _sessionmaker('sqlite+aiosqlite:///tst_database.db')

@pytest_asyncio.fixture
async def in_memory_db_sessionmaker():
    return await _in_memory_db_sessionmaker()

@pytest_asyncio.fixture    
async def config_url_sessionmaker() -> async_sessionmaker:
    assert config.DB_TYPE in ('PG', 'SQLITE')
    return await _sessionmaker(config.get_db_dsn())


@pytest_asyncio.fixture
async def in_memory_adbot_srv(in_memory_db_sessionmaker):
    adbot_srv = await AdBotServices(in_memory_db_sessionmaker)
    return adbot_srv

@pytest_asyncio.fixture
async def file_db_adbot_srv(file_db_sessionmaker):
    adbot_srv = await AdBotServices(file_db_sessionmaker)
    return adbot_srv

@pytest_asyncio.fixture
async def config_url_adbot_srv(config_url_sessionmaker):
    adbot_srv = await AdBotServices(config_url_sessionmaker)
    return adbot_srv



# ========================================================================================
# enviroument for integration tests

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
            self, ad_bot_srv: AdBotServices, bot_token: str, admin_id: int,
            message_manager=None
        ) -> None:
            super().__init__(
                ad_bot_srv=ad_bot_srv,
                bot_token=bot_token,
                redis_host='',
                redis_port=0,
                redis_db=0,
                admin_id=admin_id,
                message_manager=message_manager
            )
            self._send_bot_cmd = AsyncMock()
            self._dp.start_polling = AsyncMock()
            self._dp.stop_polling = AsyncMock()

        def _create_bot(self, bot_token: str):
            return AsyncMock(Bot)

        def _create_dp(
            self, redis_host: str, redis_port: int, redis_db: int
        ) -> Dispatcher:
            return Dispatcher(ad_bot_srv=self._ad_bot_srv)

    e = Env()
    e.ad_bot_srv = in_memory_adbot_srv
    e.message_manager = MockMessageManager()
    e.tg_bot = TestableTgBotPresentation(
        ad_bot_srv=in_memory_adbot_srv,
        bot_token='',
        admin_id=e.admin_id,
        message_manager=e.message_manager
    )

    tg_user_id = random.randint(e.admin_id + 1, e.admin_id * 10)
    e.client = BotClient(e.tg_bot._dp, tg_user_id, tg_user_id)
    e.client_admin = BotClient(e.tg_bot._dp, e.admin_id, e.admin_id)

    with patch('aiogram.types.Message.delete', new=AsyncMock()):
        with patch('aiogram.types.Message.answer', new=AsyncMock()):
            yield e 


# ========================================================================================
# Inviroument for e2e tests

async def echo_handler(message: Message, bot: Bot):
    if message.text and (message.chat.id != message.from_user.id):
        await bot.send_message(message.chat.id, message.text)


class TestableAdBotSrv(AdBotServices):
    def __ainit__(self, db_pool: async_sessionmaker):
        super().__ainit__(db_pool)
        self._resume = False

    async def resume_loop(self): # method to resume the loop
        self._resume = True
        while self._resume:
            await asyncio.sleep(0.001)
            
    async def _loop(self): # loop will suspend after each iteration
        while not self._stop:
            while (not self._resume) and (not self._stop):
                await asyncio.sleep(0.001)
            await self._loop_iter()
            self._resume = False


class TestableApp(AdBotApp):
    def __ainit__(self, client_tg_id: int):
        super().__ainit__()
        self._ad_bot_services: TestableAdBotSrv
        self._scheduler.remove_all_jobs()
        self._msg_fetcher._ignore_bots = False
        tg_bot: TGBot = self._presentation
        tg_bot._dp.message.register(
            echo_handler, SenderId(client_tg_id)
        )

    async def _db_connect(self) -> async_sessionmaker:
        return await _in_memory_db_sessionmaker()

    async def _create_ad_bot_services(
        self, db_pool: async_sessionmaker
    ) -> TestableAdBotSrv:
        ad_bot_srv = await TestableAdBotSrv(db_pool)
        ad_bot_srv._CHECK_IDLE_CYCLES = 1
        ad_bot_srv._CHECK_IDLE_INTERVAL_SEC = 1
        return ad_bot_srv

    async def fetch_messages(self):
        await self._msg_fetcher.fetch_messages()


@dataclass
class E2E_Env():
    app: Optional[TestableApp] = None
    client: Optional[TelegramClient] = None
    bot_name: str = ''
    client_id: int = 0
    test_chat_id: int = 0


@pytest.fixture(scope='session')
def e2e_confirmation():
    yn = input('Make sure that no other copy of telethon client started and type `y`: ')
    assert yn.lower() == 'y'


@pytest.fixture()
async def e2e_env(e2e_confirmation) -> E2E_Env:
    assert config.MODE == 'TEST'
    assert config.CHATS_FILTER != ''
    assert len(config.CHATS_FILTER.split(';')) == 1
    assert config.TESTBOT_NAME != ''

    e = E2E_Env()
    e.test_chat_id = int(config.CHATS_FILTER.split(';')[0])
    e.client_id = config.CLIENT_ID
    e.bot_name = config.TESTBOT_NAME
    e.app = await TestableApp(e.client_id)
    e.client = e.app._msg_fetcher._client
    
    yield e 


# ========================================================================================
# helpers

def mock_method_raise_SQLAlchemyError(*arg, **kwarg):
    raise SQLAlchemyError()


def brake_sessionmaker(db_pool: async_sessionmaker):
    def broken_session_maker():
        session = db_pool()
        session.commit = mock_method_raise_SQLAlchemyError
        session.scalar = mock_method_raise_SQLAlchemyError
        session.scalars = mock_method_raise_SQLAlchemyError
        session.execute = mock_method_raise_SQLAlchemyError
        return session

    return broken_session_maker


async def client_send_to_bot(client: TelegramClient, bot_name: str, msg: str):
    async with client:
        assert client.is_connected
        await client.send_message(bot_name, msg)
        await asyncio.sleep(0.5)

async def client_send_to_test_chat(client: TelegramClient, test_chat_id: int, msg: str):
    async with client:
        assert client.is_connected
        chat = await client.get_entity(test_chat_id)
        await client.send_message(chat, msg)
    await asyncio.sleep(0.5)



async def bot_send_to_test_chat(bot: Bot, test_chat_id: int, msg: str):
    await bot.send_message(test_chat_id, msg)
    await asyncio.sleep(0.5)


async def client_get_from_bot(client: TelegramClient, bot_name: str) -> Message:
    async with client:
        messages = client.iter_messages(bot_name, limit=1)
        async for msg in messages:
            return msg


async def client_get_my_id(client: TelegramClient) -> int:
    async with client:
        assert client.is_connected
        me: User = await client.get_entity('me')
        return me.id
