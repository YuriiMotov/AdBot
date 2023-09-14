import logging
from typing import Any

from aiogram.filters.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from magic_filter import F
from aiogram_dialog import (
    Window,
    DialogManager,
    DialogProtocol,
    ShowMode,
)
from aiogram_dialog.widgets.kbd import (
    Group,
    Select,
    Button,
    SwitchTo,
    Cancel
)
from aiogram_dialog.widgets.text import Const, Format, Case, Multi, List
from aiogram_dialog import Dialog
from aiogram_dialog.widgets.input import MessageInput

from adbot.domain.services import AdBotServices
from adbot.domain import models
from .common import (
    data_getter, get_user_data, on_unexpected_input, set_error_msg, on_menu_navigate_click,
    ERROR_MSG_FORMAT
)

logger = logging.getLogger(__name__)

# ======================================================================================================
# Settings dialog's states

class SettingsSG(StatesGroup):
    main = State()
    manage_keywords = State()
    remove_keyword = State()
    dialog_closed = State()


# ======================================================================================================
# Settings main window

async def on_subscription_toggle_click(
        callback: CallbackQuery, button: Button, manager: DialogManager
):
    ad_bot_srv: AdBotServices = manager.middleware_data.get('ad_bot_srv')
    logger.debug(f'on_subscription_toggle_click, user={callback.from_user.id}')

    try:
        user: models.User = await get_user_data(manager, ad_bot_srv)
        await ad_bot_srv.set_subscription_state(user.id, not user.subscription_state)
    except:
        logger.error(f'Exception in `on_subscription_toggle_click`')
        raise


settings_window = Window(
    # Subscription state
    Multi(
        Const("<b>Subscription state:</b>"),
        Case(
            {True: Const("✅ enabled"), False: Const("☑ disabled")},
            selector=F["user"].subscription_state
        ),
        sep=" ",
    ),
    # List of keywords
    Const(
        "<b>Your list of keywords is empty.</b>",
        when=F["user"].keywords.len() == 0,
    ),
    Multi(
        Const("<b>Your list of keywords:</b>"),
        List(Format("  - {item}"), items=F["user"].keywords),
        when=F["user"].keywords.len() > 0,
        sep="\n",
    ),
    # Warn that forwarding is suspended
    Const(
        "\n" \
            "<b>Attention!</b> \n"\
            "Message forwarding is suspended when this menu is open."
        ),
    Format(
        "\n" \
            "✉ You have {user.forward_queue_len} forwarded messages in the queue. \n" \
             "Close the menu to see them.",
       when=F["user"].forward_queue_len > 0
    ),
    # Error message
    Format(
        ERROR_MSG_FORMAT,
        when=F['dialog_data']['error_msg']
    ),

    Button(
        text=Case(
                {
                    True: Const("Disable subscription"),
                    False: Const("Enable subscription")
                },
                selector=F["user"].subscription_state
        ),
        on_click=on_subscription_toggle_click,
        id="subscription_toggle",
    ),
    SwitchTo(
        text=Const("Manage keywords"),
        id="manage_keywords_btn",
        state=SettingsSG.manage_keywords,
        on_click=on_menu_navigate_click
    ),
    Cancel(text=Const("Close menu")),
    MessageInput(on_unexpected_input),
    getter=data_getter,
    state=SettingsSG.main,
)


# ======================================================================================================
# Keywords management window

async def on_keyword_add_input(
    message: Message, dialog: DialogProtocol, manager: DialogManager
):
    """ """
    ad_bot_srv: AdBotServices = manager.middleware_data.get('ad_bot_srv')
    user = await ad_bot_srv.get_user_by_telegram_id(message.from_user.id)
    keyword = message.text
    await message.delete()
    logger.debug(f'on_keyword_add_input, user={user.id}, keyword="{keyword}"')

    try:
        await ad_bot_srv.add_keyword(user.id, keyword.strip())
    except:
        logger.error(f'on_keyword_add_input failed. User={user.id}')
        raise
    manager.show_mode = ShowMode.EDIT


manage_keywords_window = Window(
    Const(
        "<b>Your list of keywords is empty.</b>",
        when=F["user"].keywords.len() == 0,
    ),
    Multi(
        Const("<b>Your list of keywords:</b>"),
        List(Format("  - {item}"), items=F["user"].keywords),
        when=F["user"].keywords.len() > 0,
        sep="\n",
    ),
    Format(
        "\n" \
            "<b>Attention!</b> \n" \
            "The amount of keywords in your list is limited by {user.keywords_limit}. \n" \
            "<u>To add new keywords</u> you have to <u>remove</u> some existing keywords from your list.",
        when=(F["user"].keywords.len() >= F["user"].keywords_limit)
    ),
    Const(
        "\n" \
            "<u>To add a keyword write it in the chat</u>",
        when=(F["user"].keywords.len() < F["user"].keywords_limit)
    ),
    # Error message
    Format(
        ERROR_MSG_FORMAT,
        when=F['dialog_data']['error_msg']
    ),
    MessageInput(on_keyword_add_input),
    SwitchTo(
        text=Const("Remove keywords"),
        id="remove_keywords",
        state=SettingsSG.remove_keyword,
        on_click=on_menu_navigate_click
    ),
    SwitchTo(
        text=Const("Back"),
        id="back_to_main",
        state=SettingsSG.main,
        on_click=on_menu_navigate_click
    ),
    state=SettingsSG.manage_keywords,
    getter=data_getter,
)


# ======================================================================================================
# Keyword removing window

async def on_remove_kw_selected(
    callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str
):
    ad_bot_srv: AdBotServices = manager.middleware_data.get('ad_bot_srv')
    user = await ad_bot_srv.get_user_by_telegram_id(callback.from_user.id)
    logger.debug(f'on_remove_kw_selected, user={user.id}, keyword={item_id}')

    try:
        await ad_bot_srv.remove_keyword(user.id, item_id)
    except:
        logger.error(f'on_remove_kw_selected, remove_keyword failed')
        raise



remove_keyword_window = Window(
    Const(
        "Your list of keywords is empty.",
        when=F["user"].keywords.len() == 0,
    ),
    Const(
        "Choose keywords to remove:",
        when=F["user"].keywords.len() > 0,
    ),
    # Error message
    Format(
        ERROR_MSG_FORMAT,
        when=F['dialog_data']['error_msg']
    ),
    MessageInput(on_unexpected_input),
    Group(
        Select(
            Format("❌ {item}"),
            id="remove_keyword_select",
            items=F["user"].keywords,
            item_id_getter=lambda a: a,
            on_click=on_remove_kw_selected,
        ),
        width=2,
        when=F["user"].keywords.len() > 0,
    ),
    SwitchTo(
        text=Const("Back"),
        id="manage_keywords_btn",
        state=SettingsSG.manage_keywords,
        on_click=on_menu_navigate_click
    ),
    state=SettingsSG.remove_keyword,
    getter=data_getter,
)


# ======================================================================================================
# 'Dialog closed' window

dialog_closed_window = Window(
    Multi(
        Const("<b>Subscription state:</b>"),
        Case(
            {True: Const("✅ enabled"), False: Const("☑ disabled")},
            selector=F["user"].subscription_state
        ),
        sep=" ",
    ),
    # List of keywords
    Const(
        "<b>Your list of keywords is empty.</b>",
        when=F["user"].keywords.len() == 0,
    ),
    Multi(
        Const("<b>Your list of keywords:</b>"),
        List(Format("  - {item}"), items=F["user"].keywords),
        when=F["user"].keywords.len() > 0,
        sep="\n",
    ),

    Const(
        "\n" \
        "Settings menu is closed.\n" \
        "To open it again choose /menu command in the bot menu or type /menu."
        ),
    state=SettingsSG.dialog_closed,
    getter=data_getter,
)


# ======================================================================================================
# Dialog object

async def on_dialog_close(result: Any, manager: DialogManager):

    ad_bot_srv: AdBotServices = manager.middleware_data.get('ad_bot_srv')

    event = manager.event
    if hasattr(event, "from_user"):
        logger.debug(f'on_dialog_close, user={event.from_user.id}')
        user = await ad_bot_srv.get_user_by_telegram_id(event.from_user.id)
        await ad_bot_srv.set_menu_closed_state(user.id, True)
    else:
        logger.error(f'on_dialog_close. Event object class {event.__class__} doesn`t have attr "from_user"')

    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(SettingsSG.dialog_closed)
    await manager.show()


def get_dialog() -> Dialog:
    dialog = Dialog(
                settings_window,
                manage_keywords_window,
                remove_keyword_window,
                dialog_closed_window,
                on_close=on_dialog_close,
            )
    return dialog
