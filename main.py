import asyncio
import logging

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.types import Message, BotCommand, BotCommandScopeAllPrivateChats
from aiogram.filters import Command, ExceptionTypeFilter
from redis.asyncio.client import Redis
from aiogram_dialog import DialogManager, StartMode, setup_dialogs, ShowMode
from aiogram_dialog.api.exceptions import NoContextError, UnknownIntent, UnknownState
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from client_main import check_new_messages, CHECK_NEW_MESSAGES_INTERVAL
from config_reader import config
#from middlewares.db import DbSessionMiddleware
from db import models
from functions import session_decorator
from functions import bot_functions  as bf
from dialogs import settings, help        # Import dialogs
from dialogs.common import DBErrorException
from debug import debug_enable

logging.basicConfig(filename='logs/main.log', level=logging.ERROR)
if config.TEST == 1:
    debug_enable('functions.bot_functions')

logger = logging.getLogger(__name__)


async def start(message: Message, dialog_manager: DialogManager):
    logger.debug(f'`start` command, user={message.from_user.id}')
    await dialog_close(message, dialog_manager)
    user_id = message.from_user.id
    user_name = message.from_user.username
    user_data = await bf.get_user_add_refresh_reset(user_id, user_name)
    if user_data:
        await message.delete()
        await dialog_manager.start(settings.SettingsSG.main, mode=StartMode.RESET_STACK)
    else:
        logger.error(f'DB error in `start` command handler')
        await message.answer("Service unavailable. Please try later.")


async def show_help(message: Message, dialog_manager: DialogManager):
    logger.debug(f'`help` command, user={message.from_user.id}')
    await dialog_close(message, dialog_manager)
    user_id = message.from_user.id
    user_name = message.from_user.username
    user_data = await bf.get_user_add_refresh_reset(user_id, user_name)
    if user_data:
        await message.delete()
        await dialog_manager.start(help.HelpSG.main, mode=StartMode.RESET_STACK)
    else:
        logger.error(f'DB error in `help` command handler')
        await message.answer("Service unavailable. Please try later.")


async def dialog_close(message: Message, dialog_manager: DialogManager):
    logger.debug(f'`close_dialog` command, user={message.from_user.id}')
    dialog_manager.show_mode = ShowMode.EDIT
    try:
        await dialog_manager.done()
    except NoContextError:
        pass


async def dialog_refresh(message: Message, dialog_manager: DialogManager):
    logger.debug(f'`refresh_dialog` command, user={message.from_user.id}')
    try:
        dialog_manager.show_mode = ShowMode.EDIT
        await dialog_manager.show()
    except NoContextError:
        logger.warning(f'`refresh_dialog` command, user={message.from_user.id}, Exception (NoContextError)')


async def on_db_error(event, dialog_manager: DialogManager):
    logging.error(f"DB error exception: {event.exception}. Switch to error message window")
    await dialog_manager.start(
        settings.SettingsSG.db_error, mode=StartMode.RESET_STACK, show_mode=ShowMode.EDIT,
    )


async def on_unknown_intent(event, dialog_manager: DialogManager):
    logging.error(f"on_unknown_intent. Restarting dialog: {event.exception}")
    await dialog_manager.start(
        settings.SettingsSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.EDIT,
    )


async def on_unknown_state(event, dialog_manager: DialogManager):
    logging.error(f"on_unknown_state. Restarting dialog: {event.exception}")
    await dialog_manager.start(
        settings.SettingsSG.main, mode=StartMode.RESET_STACK, show_mode=ShowMode.EDIT,
    )


async def set_main_menu(bot: Bot):
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
    await bot.set_my_commands(main_menu_commands, scope=BotCommandScopeAllPrivateChats())


async def main():

    # Creating DB engine and connections pool
    engine = create_engine(config.DB_DNS, pool_pre_ping=True)
    db_pool = sessionmaker(bind=engine)

    # Change the flag to True to create DB
    if False:
        models.Base.metadata.create_all(engine)

    # Create Storage, Bot and Dispatcher objects
    storage = RedisStorage(
        redis=Redis(host='localhost', port=6379, db=config.REDIS_DB),
        key_builder=DefaultKeyBuilder(with_destiny=True)
    )
    bot = Bot(token=config.BOT_TOKEN.get_secret_value(), parse_mode='HTML')
    dp = Dispatcher(storage=storage)

    # Set telegram menu commands for this bot
    await set_main_menu(bot)

    # Add DB seession object to callback's attributes
    #dp.update.middleware(DbSessionMiddleware(session_pool=db_pool))

    # Register 'start' command handler
    dp.message.register(start, Command('start', 'settings', 'menu'))
    dp.message.register(dialog_close, Command('close_dialog'))
    dp.message.register(dialog_refresh, Command('refresh_dialog'))

    dp.message.register(show_help, Command('help'))


    # Set error handlers
    dp.errors.register(on_db_error, ExceptionTypeFilter(DBErrorException))
    dp.errors.register(
        on_unknown_intent,
        ExceptionTypeFilter(UnknownIntent),
    )
    dp.errors.register(
        on_unknown_state,
        ExceptionTypeFilter(UnknownState),
    )

    # Register dialogs and setup dialogs
    dp.include_router(settings.dialog)
    dp.include_router(help.dialog)
    setup_dialogs(dp)

    # Set sessionmaker and bot for modules
    session_decorator.set_session_maker(db_pool)
    bf.bot = bot
    bf.dp = dp

    # Create and start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(bf.process_groupchat_messages, 'interval', seconds=120)
    scheduler.add_job(check_new_messages, 'interval', seconds=CHECK_NEW_MESSAGES_INTERVAL)
    scheduler.add_job(bf.forward_messages, 'interval', seconds=120)
    scheduler.add_job(bf.check_opened_dialogs, 'interval', seconds=30)
    scheduler.start()

    # Start polling
    logger.debug(f'Start polling')
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
