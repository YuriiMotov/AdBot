import asyncio
from datetime import datetime
import logging

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramForbiddenError
from aiogram.filters import and_f, Command, ExceptionTypeFilter
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.types import (
    Chat, User, Message, Update, BotCommand, BotCommandScopeAllPrivateChats
)
from aiogram_dialog import setup_dialogs
from aiogram_dialog.api.exceptions import UnknownIntent, UnknownState
from redis.asyncio.client import Redis

from adbot.domain import events
from adbot.domain.services import AdBotServices
from adbot.domain import exceptions as exc
from . import bot_handlers
from .dialogs import settings, help, errors
from .filters import ChatId
from ..presentation_interface import PresentationInterface

logger = logging.getLogger(__name__)

class TGBot(PresentationInterface):
    def __init__(
        self, ad_bot_srv: AdBotServices, bot_token: str,
        redis_host: str, redis_port: int, redis_db: int,
        admin_id: int, message_manager=None
    ) -> None:
        
        super().__init__(ad_bot_srv)
        
        self._bot = self._create_bot(bot_token)
        self._dp = self._create_dp(redis_host, redis_port, redis_db)

        # Register command handlers
        self._dp.message.register(
            bot_handlers.start_cmd_handler,
            Command('start', 'settings', 'menu')
            )
        self._dp.message.register(
            bot_handlers.dialog_close_cmd_handler, Command('close_dialog')
        )
        self._dp.message.register(
            bot_handlers.dialog_refresh_cmd_handler, Command('refresh_dialog')
        )
        self._dp.message.register(
            bot_handlers.show_help, Command('help')
        )
        self._dp.message.register(
            bot_handlers.stop_bot, and_f(Command('stop_bot'), ChatId(admin_id))
        )

        # Set error handlers
        self._dp.errors.register(
            bot_handlers.on_db_error,
            ExceptionTypeFilter(exc.AdBotExceptionSQL, exc.AdBotExceptionUserNotExist)
        )
        self._dp.errors.register(
            bot_handlers.on_unknown_intent,
            ExceptionTypeFilter(UnknownIntent),
        )
        self._dp.errors.register(
            bot_handlers.on_unknown_state,
            ExceptionTypeFilter(UnknownState),
        )

        # Register dialogs and setup dialogs
        self._dp.include_router(settings.get_dialog())
        self._dp.include_router(help.get_dialog())
        self._dp.include_router(errors.get_dialog())
        setup_dialogs(self._dp, message_manager=message_manager)
        
        # Subscribe for events from services
        self._subscribe_for_events()


    def _subscribe_for_events(self):
        self._ad_bot_srv.messagebus.subscribe(
            [events.AdBotInactivityTimeout], self.user_inactivity_timeout_handler
        )
        self._ad_bot_srv.messagebus.subscribe(
            [events.AdBotMessageForwardRequest], self.user_message_forward_request_handler
        )
        self._ad_bot_srv.messagebus.subscribe(
            [events.AdBotUserDataUpdated], self.user_data_updated_handler
        )
        self._ad_bot_srv.messagebus.subscribe(
            [events.AdBotStop], self.stop_event_handler
        )


    def _create_bot(self, bot_token: str) -> Bot:
        return Bot(token=bot_token, parse_mode='HTML')


    def _create_dp(self, redis_host: str, redis_port: int, redis_db: int) -> Dispatcher:
        storage = RedisStorage(
            redis=Redis(host=redis_host, port=redis_port, db=redis_db),
            key_builder=DefaultKeyBuilder(with_destiny=True)
        )
        return Dispatcher(storage=storage, ad_bot_srv=self._ad_bot_srv)


    async def _set_main_menu(self, bot: Bot):
        main_menu_commands = [
            BotCommand(
                command="/menu",
                description="Open settings menu"
            ),
            BotCommand(
                command="/help",
                description="Show help"
            )
        ]
        await bot.set_my_commands(main_menu_commands)
        await bot.set_my_commands(
            main_menu_commands, scope=BotCommandScopeAllPrivateChats()
        )


    async def run(self):
        # Set telegram menu commands for this bot
        await self._set_main_menu(self._bot)
        logger.debug(f'Start polling')
        await self._dp.start_polling(self._bot)


    async def stop_event_handler(self, event: events.AdBotStop):
        if self._dp._running_lock.locked():
            await self._dp.stop_polling()


    async def user_inactivity_timeout_handler(self, event: events.AdBotInactivityTimeout):
        try:
            user = await self._ad_bot_srv.get_user_by_id(event.user_id)
        except exc.AdBotExceptionSQL:
            return
        await self._send_bot_cmd('/close_dialog', user.telegram_id)


    async def user_data_updated_handler(self, event: events.AdBotUserDataUpdated):
        try:
            user = await self._ad_bot_srv.get_user_by_id(event.user_id)
        except exc.AdBotExceptionSQL:
            return
        await self._send_bot_cmd('/refresh_dialog', user.telegram_id)
    

    async def user_message_forward_request_handler(
        self, event: events.AdBotMessageForwardRequest
    ):
        try:
            await self._bot.send_message(event.telegram_id, event.message_url)
        except TelegramForbiddenError as e:
            if e.message.find('bot was blocked by the user') >= 0:
                logger.warning(f'Bot was blocked by user {event.telegram_id}. Unsubscribe user')
                await self._ad_bot_srv.set_subscription_state(event.user_id, False)
                await self._ad_bot_srv.set_menu_closed_state(event.user_id, True)
            else:
                raise


    async def _send_bot_cmd(self, cmd: str, user_tg_id: int):
        """
            Sends telegram command from user to bot.
            Raises
                ... TODO ...
        """
        logger.debug(f'_bot_send_command {user_tg_id}, {cmd}')
        user = User(id=user_tg_id, is_bot=False, first_name='')
        chat = Chat(id=user_tg_id, type='private')
        message = Message(
            message_id=0,
            date=datetime.now(),
            chat=chat,
            from_user=user,
            text=cmd
        )
        update = Update(update_id=0, message=message)
        await self._dp.propagate_event(
            update_type="update",
            event=update,
            bot=self._bot,
            event_from_user=user,
            event_chat=chat,
            **self._dp.workflow_data
        )
        return True