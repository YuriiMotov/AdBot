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

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class DBErrorException(Exception):
    pass


# ======================================================================================================
# Settings dialog's states

class SettingsSG(StatesGroup):
    main = State()
    manage_keywords = State()
    remove_keyword = State()
    dialog_closed = State()
    db_error = State()


# ======================================================================================================
# Common dialog functions

async def get_user_data(manager: DialogManager) -> bf.UserDict:
    return await bf.get_user(int(manager.event.from_user.id))


async def data_getter(dialog_manager: DialogManager, **kwargs):
    user_data = await get_user_data(dialog_manager)
    if user_data:
        return {'user': user_data}
    else:
        raise DBErrorException()


async def on_unexpected_input(
    message: Message, dialog: DialogProtocol, manager: DialogManager
):
    """
    Handle unexpacted text input from user. Just delete message.
    """
    await message.delete()
    manager.show_mode = ShowMode.EDIT


async def on_menu_navigate_click(
        callback: CallbackQuery, button: Button, manager: DialogManager
):
    await bf.reset_inactivity_timer(manager.event.from_user.id)


# ======================================================================================================
# Settings main window

async def on_forwarding_toggle_click(
        callback: CallbackQuery, button: Button, manager: DialogManager
):
    user_data = await get_user_data(manager)
    if user_data is None:
        logging.error(f'on_forwarding_toggle_click, user data is None')
        return
    if (await bf.set_forwarding_state(user_data['id'], not user_data["forwarding"])) == False:
        logging.error(f'on_forwarding_toggle_click, set_forwarding_state returned False')
        return

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
    user_id = manager.event.from_user.id
    if not (await bf.add_keyword(user_id, message.text.strip())):
        logger.error(f'on_keyword_add_input {user_id}, add_keyword failed')
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
    user_id = manager.event.from_user.id
    if not await bf.remove_keyword(user_id, item_id):
        logger.error(f'on_remove_kw_selected {user_id}, remove_keyword failed')
        callback.answer("Error..", show_alert=True)


remove_keyword_window = Window(
    Const(
        "Your list of keywords is empty.",
        when=F["user"]["keywords"].len() == 0,
    ),
    Const(
        "Choose keywords to remove:",
        when=F["user"]["keywords"].len() > 0,
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
        "To open it again choose /settings command in the bot menu or type /settings."
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
    await bf.set_menu_closed_state(manager.event.from_user.id, True)
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
