import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from adbot.domain.events import AdBotStop
from adbot.domain.services import AdBotServices
from adbot.presentation.telegram.tg_bot import TGBot
from adbot.presentation.presentation_interface import PresentationInterface
from adbot.message_fetcher.telegram.telegram_fetcher import TelegramMessageFetcher
from adbot.message_fetcher.interface import MessageFetcher
from .config_reader import config

logger = logging.getLogger(__name__)

CHECK_NEW_MESSAGES_INTERVAL_SEC = 30


class AdBotApp():

    def __init__(self) -> None:
        db_pool = self._db_connect()
        self._ad_bot_services: AdBotServices = self._create_ad_bot_services(db_pool)
        self._presentation: PresentationInterface = self._create_tg_bot(
            self._ad_bot_services
        )
        self._scheduler = AsyncIOScheduler()
        self._msg_fetcher: MessageFetcher = self._create_message_fetcher()

    async def run(self):
        self._scheduler.start()
        await asyncio.wait(
            [
                asyncio.create_task(self._ad_bot_services.run()),
                asyncio.create_task(self._presentation.run())
            ],
            return_when=asyncio.tasks.FIRST_COMPLETED
        )

    async def stop(self, event: AdBotStop):
        self._scheduler.shutdown()


    def _db_connect(self) -> sessionmaker:
        engine = create_engine(config.DB_DNS, pool_pre_ping=True)
        return sessionmaker(bind=engine)

    def _create_ad_bot_services(self, db_pool: sessionmaker) -> AdBotServices:
        return AdBotServices(db_pool)

    def _create_tg_bot(self, ad_bot_services: AdBotServices) -> PresentationInterface:
        tg_bot = TGBot(
            ad_bot_srv=ad_bot_services,
            bot_token=config.BOT_TOKEN.get_secret_value(),
            redis_db=config.REDIS_DB,
            admin_id=config.ADMIN_ID
        )
        return tg_bot

    def _create_message_fetcher(self) -> MessageFetcher:
        chats = None
        if config.CHATS_FILTER != '':
            chats = list(map(int, config.CHATS_FILTER.split(';')))

        tg_fetcher = TelegramMessageFetcher(
            self._ad_bot_services.add_message, 
            config.API_ID,
            config.API_HASH.get_secret_value(),
            chats_filter=chats
        )

        self._scheduler.add_job(
            tg_fetcher.fetch_messages, 'interval', seconds=CHECK_NEW_MESSAGES_INTERVAL_SEC
        )

        return tg_fetcher


