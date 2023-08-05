import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.types import Message, BotCommand
from aiogram.filters import CommandStart, Command
from redis.asyncio.client import Redis
from aiogram_dialog import DialogManager, StartMode, setup_dialogs, ShowMode
from aiogram_dialog.api.exceptions import NoContextError
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from client_main import check_new_messages, CHECK_NEW_MESSAGES_INTERVAL
from config_reader import config
#from middlewares.db import DbSessionMiddleware
from db import models
from functions import session_decorator
from functions import bot_functions  as bf
from dialogs import settings        # Import dialogs


async def start(message: Message, dialog_manager: DialogManager):
    await message.delete()
    await dialog_manager.start(settings.SettingsSG.main, mode=StartMode.RESET_STACK)


async def dialog_close(message: Message, dialog_manager: DialogManager):
    try:
        await dialog_manager.done()
    except NoContextError:
        pass


async def dialog_refresh(message: Message, dialog_manager: DialogManager):
    try:
        dialog_manager.show_mode = ShowMode.EDIT
        await dialog_manager.show()
    except NoContextError:
        pass



async def set_main_menu(bot: Bot):
    main_menu_commands = [
        BotCommand(
            command="/start",
            description="Open settings menu"
        ),
        BotCommand(
            command="/help",
            description="Show help"
        )
    ]
    await bot.set_my_commands(main_menu_commands)


async def main():
    # Creating DB engine and connections pool
    engine = create_engine(config.DB_DNS, pool_pre_ping=True)
    db_pool = sessionmaker(bind=engine)

    # Change the flag to True to create DB
    if True:
        models.Base.metadata.create_all(engine)

    # Create Storage, Bot and Dispatcher objects
    storage = RedisStorage(
        redis=Redis(host='localhost', port=6379, db=4),
        key_builder=DefaultKeyBuilder(with_destiny=True)
    )
    bot = Bot(token=config.BOT_TOKEN.get_secret_value(), parse_mode='HTML')
    dp = Dispatcher(storage=storage)

    # Set telegram menu commands for this bot
    await set_main_menu(bot)

    # Add DB seession object to callback's attributes
    #dp.update.middleware(DbSessionMiddleware(session_pool=db_pool))

    # Register 'start' command handler
    dp.message.register(start, CommandStart())
    dp.message.register(dialog_close, Command('close_dialog'))
    dp.message.register(dialog_refresh, Command('refresh_dialog'))


    # Register dialogs and setup dialogs
    dp.include_router(settings.dialog)
    setup_dialogs(dp)

    # Set sessionmaker and bot for modules
    session_decorator.set_session_maker(db_pool)
    bf.bot = bot
    bf.dp = dp

    # Create and start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(bf.process_groupchat_messages, 'interval', seconds=30)
    scheduler.add_job(check_new_messages, 'interval', seconds=CHECK_NEW_MESSAGES_INTERVAL)
    scheduler.add_job(bf.forward_messages, 'interval', seconds=10)
    scheduler.add_job(bf.check_opened_dialogs, 'interval', seconds=20)
    scheduler.start()

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
