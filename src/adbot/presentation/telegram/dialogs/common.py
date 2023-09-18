import logging
from typing import Optional

from aiogram.types import Message, CallbackQuery
from aiogram_dialog import (
    DialogManager,
    DialogProtocol,
    ShowMode,
)
from aiogram_dialog.widgets.kbd import Button

from adbot.domain.services import AdBotServices
from adbot.domain import models

logger = logging.getLogger(__name__)

ERROR_MSG_FORMAT = '\n ⚠ Error occurred. {dialog_data[error_msg]} Try again later.'


async def get_user_data(
        manager: DialogManager, ad_bot_srv: AdBotServices
    ) -> Optional[models.User]:
    event = manager.event
    if hasattr(event, "from_user"):
        return await ad_bot_srv.get_user_by_telegram_id(int(manager.event.from_user.id))
    else:
        logger.error(
            f'get_user_data, event class {event.__class__} ' \
            'doesn`t have attr "from_user"'
        )


async def data_getter(dialog_manager: DialogManager, ad_bot_srv: AdBotServices, **kwargs):
    event = dialog_manager.event

    logger.debug(f'data_getter, event class {event.__class__}')

    if isinstance(event, Message) and (event.text == '/refresh_dialog'):
        pass
    else:
        check_error_msg(dialog_manager)

    user = await get_user_data(dialog_manager, ad_bot_srv)

    return {'user': user}
    

async def on_unexpected_input(
    message: Message, dialog: DialogProtocol, manager: DialogManager
):
    """
    Handle unexpacted text input from user. Just delete message.
    """
    state = '???'
    context = manager.current_context()
    if context and hasattr(context, "state"):
        state = context.state
    logger.warning(f'on_unexpected_input, user={message.from_user.id}, state="{state}", text="{message.text}"')

    await message.delete()
    manager.show_mode = ShowMode.EDIT


def set_error_msg(manager: DialogManager, msg: str):
    manager.dialog_data['error_msg'] = msg
    manager.dialog_data['error_msg_counter'] = 1


def check_error_msg(manager: DialogManager):
    counter = manager.dialog_data.get('error_msg_counter', 0)
    if counter > 0:
        manager.dialog_data['error_msg_counter'] -= 1
    else:
        manager.dialog_data['error_msg'] = ''


async def on_menu_navigate_click(
        callback: CallbackQuery, button: Button, manager: DialogManager
):
    ad_bot_srv: AdBotServices = manager.middleware_data.get('ad_bot_srv')
    user = await ad_bot_srv.get_user_by_telegram_id(callback.from_user.id)
    logger.debug(f'on_menu_navigate_click, user={user.id}, button={button.widget_id}')
    await ad_bot_srv.reset_inactivity_timer(user.id)

