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


# ======================================================================================================
# Settings dialog's states

class SettingsSG(StatesGroup):
    main = State()
    manage_keywords = State()
    remove_keyword = State()
    dialog_closed = State()


# ======================================================================================================
# Common dialog functions

async def data_getter(dialog_manager: DialogManager, **kwargs):

    if 'user_id' not in dialog_manager.dialog_data:
        dialog_manager.dialog_data['user_id'] = int(dialog_manager.event.from_user.id)

    user = await bf.get_user(int(dialog_manager.dialog_data.get("user_id")))
    # Create user if not exists in DB
    if user is None:
        user_name = dialog_manager.event.from_user.username
        user = await bf.add_user(
            int(dialog_manager.dialog_data.get("user_id")), user_name
        )

    dialog_manager.dialog_data["user"] = user

    return {}


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
    await bf.reset_inactivity_timer(int(manager.event.from_user.id))


# ======================================================================================================
# Settings main window

async def on_forwarding_toggle_click(
        callback: CallbackQuery, button: Button, manager: DialogManager
):
    user = manager.dialog_data.get("user")
    if user:
        manager.dialog_data['user'] = await bf.set_forwarding_state(user['id'], not user["forwarding"])


settings_window = Window(
    # Forwarding state
    Multi(
        Const("<b>Forwarding state:</b>"),
        Case(
            {True: Const("✅ enabled"), False: Const("☑ disabled")},
            selector=F["dialog_data"]["user"]["forwarding"]
        ),
        sep=" ",
    ),
    # List of keywords
    Const(
        "<b>Your list of keywords is empty.</b>",
        when=F["dialog_data"]["user"]["keywords"].len() == 0,
    ),
    Multi(
        Const("<b>Your list of keywords:</b>"),
        List(Format("  - {item}"), items=F["dialog_data"]["user"]["keywords"]),
        when=F["dialog_data"]["user"]["keywords"].len() > 0,
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
            "✉ You have {dialog_data[user][msgs_queue_len]} forwarded messages in the queue. \n" \
             "Close the menu to see them.",
        when=F["dialog_data"]["user"]["msgs_queue_len"] > 0
    ),

    Button(
        text=Case(
                {
                    True: Const("Disable message forwarding"),
                    False: Const("Enable message forwarding")
                },
                selector=F["dialog_data"]["user"]["forwarding"]
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
    state=SettingsSG.main,
)


# ======================================================================================================
# Keywords management window

async def on_keyword_add_input(
    message: Message, dialog: DialogProtocol, manager: DialogManager
):
    """ """
    user = manager.dialog_data.get("user")
    if user:
        manager.dialog_data['user'] = await bf.add_keyword(user['id'], message.text.strip())
    else:
        pass  # TODO: Show error message

    await message.delete()
    manager.show_mode = ShowMode.EDIT


manage_keywords_window = Window(
    Const(
        "<b>Your list of keywords is empty.</b>",
        when=F["dialog_data"]["user"]["keywords"].len() == 0,
    ),
    Multi(
        Const("<b>Your list of keywords:</b>"),
        List(Format("  - {item}"), items=F["dialog_data"]["user"]["keywords"]),
        when=F["dialog_data"]["user"]["keywords"].len() > 0,
        sep="\n",
    ),
    Format(
        "\n" \
            "<b>Attention!</b> \n" \
            "The amount of keywords in your list is limited by {dialog_data[user][keywords_limit}. \n" \
            "<u>To add new keywords</u> you have to <u>remove</u> some existing keywords from your list.",
        when=(F["dialog_data"]["user"]["keywords"].len() >= F["dialog_data"]["user"]["keywords_limit"])
    ),
    Const(
        "\n" \
            "<u>To add a keyword write it in the chat</u>",
        when=(F["dialog_data"]["user"]["keywords"].len() < F["dialog_data"]["user"]["keywords_limit"])
    ),

    MessageInput(on_keyword_add_input),
    SwitchTo(
        text=Const("Remove keywords"),
        id="remove_keywords",
        state=SettingsSG.remove_keyword,
        on_click=on_menu_navigate_click
    ),
    SwitchTo(text=Const("Back"), id="back_to_main", state=SettingsSG.main),
    state=SettingsSG.manage_keywords,
)


# ======================================================================================================
# Keyword removing window

async def on_remove_kw_selected(
    callback: CallbackQuery, widget: Any, manager: DialogManager, item_id: str
):
    user = manager.dialog_data.get("user")
    if user:
        manager.dialog_data['user'] = await bf.remove_keyword(user['id'], item_id)


remove_keyword_window = Window(
    Const(
        "Your list of keywords is empty.",
        when=F["dialog_data"]["user"]["keywords"].len() == 0,
    ),
    Const(
        "Choose keywords to remove:",
        when=F["dialog_data"]["user"]["keywords"].len() > 0,
    ),
    MessageInput(on_unexpected_input),
    Group(
        Select(
            Format("❌ {item}"),
            id="remove_keyword_select",
            items=F['dialog_data']['user']['keywords'],
            item_id_getter=lambda a: a,
            on_click=on_remove_kw_selected,
        ),
        width=2,
        when=F["dialog_data"]["user"]["keywords"].len() > 0,
    ),
    SwitchTo(
        text=Const("Back"),
        id="manage_keywords_btn",
        state=SettingsSG.manage_keywords,
        on_click=on_menu_navigate_click
    ),
    state=SettingsSG.remove_keyword,
)


# ======================================================================================================
# 'Dialog closed' window

dialog_closed_window = Window(
    Multi(
        Const("<b>Forwarding state:</b>"),
        Case(
            {True: Const("✅ enabled"), False: Const("☑ disabled")},
            selector=F["dialog_data"]["user"]["forwarding"]
        ),
        sep=" ",
    ),
    # List of keywords
    Const(
        "<b>Your list of keywords is empty.</b>",
        when=F["dialog_data"]["user"]["keywords"].len() == 0,
    ),
    Multi(
        Const("<b>Your list of keywords:</b>"),
        List(Format("  - {item}"), items=F["dialog_data"]["user"]["keywords"]),
        when=F["dialog_data"]["user"]["keywords"].len() > 0,
        sep="\n",
    ),

    Const(
        "\n" \
        "Settings menu is closed.\n" \
        "To open it again choose /settings command in the bot menu or type /settings."
        ),
    state=SettingsSG.dialog_closed,
)


# ======================================================================================================
# Dialog object

async def on_dialog_start(start_data: Any, manager: DialogManager):
    user_id = int(manager.event.from_user.id)
    await bf.reset_inactivity_timer(user_id)
    await bf.refresh_user_data(user_id)
    await bf.set_menu_closed_state(user_id, False)


async def on_dialog_close(result: Any, manager: DialogManager):
    await bf.set_menu_closed_state(int(manager.event.from_user.id), True)
    manager.show_mode = ShowMode.EDIT
    await manager.switch_to(SettingsSG.dialog_closed)
    await manager.show()

 
dialog = Dialog(
    settings_window,
    manage_keywords_window,
    remove_keyword_window,
    dialog_closed_window,
    getter=data_getter,
    on_start=on_dialog_start,
    on_close=on_dialog_close,
)
