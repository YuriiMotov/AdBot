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

from functions import bot_functions as bf
from dialogs.common import (
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
    db_error = State()


# ======================================================================================================
# Settings main window

async def on_forwarding_toggle_click(
        callback: CallbackQuery, button: Button, manager: DialogManager
):
    logger.debug(f'on_forwarding_toggle_click, user={callback.from_user.id}')

    user_data = await get_user_data(manager)
    if user_data:
        if (await bf.set_forwarding_state(user_data['id'], not user_data["forwarding"])) == True:
            return  # Success
        else:
            logger.error(f'on_forwarding_toggle_click, set_forwarding_state returned False')
    else:
        logger.error(f'on_forwarding_toggle_click, user data is None')

    set_error_msg(manager, 'State hasn`t been changed.')


settings_window = Window(
    # Forwarding state
    Multi(
        Const("<b>Forwarding state:</b>"),
        Case(
            {True: Const("✅ enabled"), False: Const("☑ disabled")},
            selector=F["user"]["forwarding"]
        ),
        sep=" ",
    ),
    # List of keywords
    Const(
        "<b>Your list of keywords is empty.</b>",
        when=F["user"]["keywords"].len() == 0,
    ),
    Multi(
        Const("<b>Your list of keywords:</b>"),
        List(Format("  - {item}"), items=F["user"]["keywords"]),
        when=F["user"]["keywords"].len() > 0,
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
            "✉ You have {user[msgs_queue_len]} forwarded messages in the queue. \n" \
             "Close the menu to see them.",
       when=F["user"]["msgs_queue_len"] > 0
    ),
    # Error message
    Format(
        ERROR_MSG_FORMAT,
        when=F['dialog_data']['error_msg']
    ),

    Button(
        text=Case(
                {
                    True: Const("Disable message forwarding"),
                    False: Const("Enable message forwarding")
                },
                selector=F["user"]["forwarding"]
        ),
        on_click=on_forwarding_toggle_click,
        id="forwarding_toggle",
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
    user_id = message.from_user.id

    logger.debug(f'on_keyword_add_input, user={user_id}, keyword="{message.text}"')

    if not (await bf.add_keyword(user_id, message.text.strip())):
        logger.error(f'on_keyword_add_input {user_id}, add_keyword failed')
        set_error_msg(manager, 'Keyword wasn`t added.')

    await message.delete()
    manager.show_mode = ShowMode.EDIT


manage_keywords_window = Window(
    Const(
        "<b>Your list of keywords is empty.</b>",
        when=F["user"]["keywords"].len() == 0,
    ),
    Multi(
        Const("<b>Your list of keywords:</b>"),
        List(Format("  - {item}"), items=F["user"]["keywords"]),
        when=F["user"]["keywords"].len() > 0,
        sep="\n",
    ),
    Format(
        "\n" \
            "<b>Attention!</b> \n" \
            "The amount of keywords in your list is limited by {user[keywords_limit}. \n" \
            "<u>To add new keywords</u> you have to <u>remove</u> some existing keywords from your list.",
        when=(F["user"]["keywords"].len() >= F["user"]["keywords_limit"])
    ),
    Const(
        "\n" \
            "<u>To add a keyword write it in the chat</u>",
        when=(F["user"]["keywords"].len() < F["user"]["keywords_limit"])
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
    user_id = callback.from_user.id
    logger.debug(f'on_remove_kw_selected, user={user_id}, keyword={item_id}')

    if not await bf.remove_keyword(user_id, item_id):
        logger.error(f'on_remove_kw_selected, remove_keyword failed')
        set_error_msg(manager, 'Keyword wasn`t removed.')


remove_keyword_window = Window(
    Const(
        "Your list of keywords is empty.",
        when=F["user"]["keywords"].len() == 0,
    ),
    Const(
        "Choose keywords to remove:",
        when=F["user"]["keywords"].len() > 0,
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
            items=F["user"]["keywords"],
            item_id_getter=lambda a: a,
            on_click=on_remove_kw_selected,
        ),
        width=2,
        when=F["user"]["keywords"].len() > 0,
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
        Const("<b>Forwarding state:</b>"),
        Case(
            {True: Const("✅ enabled"), False: Const("☑ disabled")},
            selector=F["user"]["forwarding"]
        ),
        sep=" ",
    ),
    # List of keywords
    Const(
        "<b>Your list of keywords is empty.</b>",
        when=F["user"]["keywords"].len() == 0,
    ),
    Multi(
        Const("<b>Your list of keywords:</b>"),
        List(Format("  - {item}"), items=F["user"]["keywords"]),
        when=F["user"]["keywords"].len() > 0,
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
# 'Dialog closed' window

db_error_window = Window(
    Const("<b>DB connection error. Please try later.</b>"),
    state=SettingsSG.db_error,
)


# ======================================================================================================
# Dialog object

async def on_dialog_close(result: Any, manager: DialogManager):
    event = manager.event
    if hasattr(event, "from_user"):
        logger.debug(f'on_dialog_close, user={event.from_user.id}')
        await bf.set_menu_closed_state(event.from_user.id, True)
    else:
        logger.error(f'on_dialog_close. Event object class {event.__class__} doesn`t have attr "from_user"')

    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(SettingsSG.dialog_closed)
    await manager.show()

 
dialog = Dialog(
    settings_window,
    manage_keywords_window,
    remove_keyword_window,
    dialog_closed_window,
    db_error_window,
    on_close=on_dialog_close,
)
