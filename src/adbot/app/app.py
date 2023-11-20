import asyncio
import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker


from adbot.domain.events import AdBotStop
from adbot.domain import models
from adbot.domain.services import AdBotServices
from adbot.presentation.telegram.tg_bot import TGBot
from adbot.presentation.presentation_interface import PresentationInterface
from adbot.message_fetcher.telegram.telegram_fetcher import TelegramMessageFetcher
from adbot.message_fetcher.interface import MessageFetcher
from .config_reader import config
from ..common.async_mixin import AsyncMixin

logger = logging.getLogger(__name__)

CHECK_NEW_MESSAGES_INTERVAL_SEC = 200


class AdBotApp(AsyncMixin):

    def __init__(self):
        """
            Object initialisation implemented in __ainit__().
            To initialise object it has to be awaited after creation
            (o = await AdBotApp()).
        """
        super().__init__()

    async def __ainit__(self) -> None:
        db_pool = await self._db_connect()
        self._ad_bot_services: AdBotServices = await self._create_ad_bot_services(db_pool)
        self._presentation: PresentationInterface = self._create_tg_bot(
            self._ad_bot_services
        )
        self._scheduler = AsyncIOScheduler()
        self._msg_fetcher: Optional[MessageFetcher] = self._create_message_fetcher()

    async def run(self):
        self._scheduler.start()
        done, pending = await asyncio.wait(
            [
                asyncio.create_task(
                    self._ad_bot_services.run(), name='ad_bot_services.run()'
                ),
                asyncio.create_task(self._presentation.run(), name='_presentation.run()')
            ],
            return_when=asyncio.tasks.FIRST_COMPLETED
        )
        for task in done:
            if task.exception():
                logger.error(
                    f'Task `{task.get_name()}` finished with exception ' \
                        '({task.exception()}).'
                )
            else:
                logger.debug(f'Task `{task.get_name()}` finished.')
        
        tasks = asyncio.gather(*pending, return_exceptions=True)
        try:
            await asyncio.wait_for(tasks, timeout=5)
        except asyncio.exceptions.TimeoutError:
            logger.warning(f'Timeout occured. Some tasks will be cancelled')

        try:
            await tasks
        except asyncio.exceptions.CancelledError:
            pass


    async def stop(self, event: AdBotStop):
        self._scheduler.shutdown()


    async def _db_connect(self) -> sessionmaker:
        engine = create_async_engine(config.get_db_dsn(), pool_pre_ping=True)
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)
        return async_sessionmaker(bind=engine, expire_on_commit=False)

    async def _create_ad_bot_services(self, db_pool: sessionmaker) -> AdBotServices:
        return await AdBotServices(db_pool)

    def _create_tg_bot(self, ad_bot_services: AdBotServices) -> PresentationInterface:
        tg_bot = TGBot(
            ad_bot_srv=ad_bot_services,
            bot_token=config.BOT_TOKEN.get_secret_value(),
            redis_host=config.REDIS_HOST,
            redis_port=config.REDIS_PORT,
            redis_db=config.REDIS_DB,
            admin_id=config.ADMIN_ID
        )
        return tg_bot

    def _create_message_fetcher(self) -> Optional[MessageFetcher]:

        if config.MODE in ('DEPLOY', 'TEST'):
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
                tg_fetcher.fetch_messages, 'interval',
                seconds=CHECK_NEW_MESSAGES_INTERVAL_SEC
            )

            return tg_fetcher
        else:
            print(f'Message fetcher creation skipped. ({config.MODE=})')
            return None


