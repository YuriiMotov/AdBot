import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage, DefaultKeyBuilder
from aiogram.types import Message, BotCommand
from aiogram.filters import CommandStart
from redis.asyncio.client import Redis
from aiogram_dialog import DialogManager, StartMode, setup_dialogs
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config_reader import config
#from middlewares.db import DbSessionMiddleware
from db import models
from functions import session_decorator
from functions.bot_functions import forward_messages
from dialogs import settings        # Import dialogs


async def start(message: Message, dialog_manager: DialogManager):
    await message.delete()
    await dialog_manager.start(settings.SettingsSG.main, mode=StartMode.RESET_STACK)


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

    # Register dialogs and setup dialogs
    dp.include_router(settings.dialog)
    setup_dialogs(dp)

    # Set sessionmaker for modules
    session_decorator.set_session_maker(db_pool)

    # Create and start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(forward_messages, 'interval', seconds=30)
    scheduler.start()

    # Start polling
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
