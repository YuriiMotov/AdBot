import logging

from aiogram.types import Message
from aiogram_dialog import DialogManager, StartMode, ShowMode
from aiogram_dialog.api.exceptions import NoContextError

from adbot.domain import exceptions as exc
from adbot.domain.services import AdBotServices
from . import dialogs

logger = logging.getLogger(__name__)


async def _send_service_unavailable_error_msg(dialog_manager: DialogManager):
    await dialog_manager.start(
        dialogs.errors.ErrorsSG.service_unavailable,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.EDIT,
    )


async def start_cmd_handler(
    message: Message, dialog_manager: DialogManager, ad_bot_srv: AdBotServices
):
    logger.debug(f'`start` command, user={message.from_user.id}')
    await message.delete()
    user_telegram_id = message.from_user.id
    user_telegram_name = message.from_user.username
    try:
        user_data = await ad_bot_srv.get_or_create_user_by_telegram_data(
            user_telegram_id, user_telegram_name
        )
        await dialog_close_cmd_handler(message, dialog_manager=dialog_manager)
        await dialog_manager.start(
            dialogs.settings.SettingsSG.main, mode=StartMode.RESET_STACK
        )
        await ad_bot_srv.set_menu_closed_state(user_data.id, False)
    except exc.AdBotException:
        logger.error(f'DB error in `start` command handler')
        raise


async def show_help(
    message: Message, dialog_manager: DialogManager, ad_bot_srv: AdBotServices
):
    logger.debug(f'`help` command, user={message.from_user.id}')
    await message.delete()
    user_telegram_id = message.from_user.id
    user_telegram_name = message.from_user.username
    try:
        user_data = await ad_bot_srv.get_or_create_user_by_telegram_data(
            user_telegram_id, user_telegram_name
        )
        await dialog_close_cmd_handler(message, dialog_manager=dialog_manager)
        await dialog_manager.start(dialogs.help.HelpSG.main, mode=StartMode.RESET_STACK)
        await ad_bot_srv.set_menu_closed_state(user_data.id, False)
    except exc.AdBotException:
        logger.error(f'DB error in `help` command handler')
        raise


async def stop_bot(
    message: Message, dialog_manager: DialogManager, ad_bot_srv: AdBotServices
):
    await ad_bot_srv.stop()


async def dialog_close_cmd_handler(message: Message, dialog_manager: DialogManager):
    logger.debug(f'`close_dialog` command, user={message.from_user.id}')
    dialog_manager.show_mode = ShowMode.EDIT
    try:
        if dialog_manager.has_context():
            await dialog_manager.done()
    except NoContextError:
        pass


async def dialog_refresh_cmd_handler(message: Message, dialog_manager: DialogManager):
    logger.debug(f'`refresh_dialog` command, user={message.from_user.id}')
    try:
        dialog_manager.show_mode = ShowMode.EDIT
        await dialog_manager.show()
    except NoContextError:
        logger.warning(
            f'`refresh_dialog` command, user={message.from_user.id}, '\
                'Exception (NoContextError)'
        )


async def on_db_error(event, dialog_manager: DialogManager):
    logger.error(f"DB error exception: {event.exception}. Switch to error message window")
    await _send_service_unavailable_error_msg(dialog_manager)


async def on_unknown_intent(event, dialog_manager: DialogManager):
    logger.error(f"on_unknown_intent. Restart dialog: {event.exception}")
    await dialog_manager.start(
        dialogs.settings.SettingsSG.main,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.EDIT,
    )


async def on_unknown_state(event, dialog_manager: DialogManager):
    logger.error(f"on_unknown_state. Restart dialog: {event.exception}")
    await dialog_manager.start(
        dialogs.settings.SettingsSG.main,
        mode=StartMode.RESET_STACK,
        show_mode=ShowMode.EDIT,
    )



