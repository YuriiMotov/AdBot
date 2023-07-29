from typing import Any, Awaitable

from sqlalchemy.orm import Session
from aiogram.filters.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery

from magic_filter import F

from aiogram_dialog import (
    Window,
    DialogManager,
    DialogProtocol,
    Data,
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


# ======================================================================================================
# Common dialog functions

async def data_getter(dialog_manager: DialogManager, **kwargs):
    user: dict = None
    if "user" not in dialog_manager.dialog_data:
        dialog_manager.dialog_data.update(
            user_id=int(dialog_manager.event.from_user.id)
        )
        user_name = dialog_manager.event.from_user.username
        user = await bf.get_user(dialog_manager.dialog_data.get("user_id"))

        # TODO: handle DB access error

        # Create user if not exists in DB
        if user is None:
            user = await bf.add_user(
                dialog_manager.dialog_data.get("user_id"), user_name
            )

        dialog_manager.dialog_data["user"] = user
    else:
        user = dialog_manager.dialog_data["user"]

    if user:
        return {
            # Need it because 'Select' doesn't allow to use function as a parameter 'item'
            "keywords": user["keywords"]
        }
    else:
        return {}


async def on_unexpected_input(
    message: Message, dialog: DialogProtocol, manager: DialogManager
):
    """
    Handle unexpacted text input from user. Just delete message.
    """
    await message.delete()
    manager.show_mode = ShowMode.EDIT




# ======================================================================================================
# Settings main window

async def on_forwarding_toggle_click(
        callback: CallbackQuery, button: Button, manager: DialogManager
):
    print('On click...')
    user = manager.dialog_data.get("user")
    if user:
        await bf.set_forwarding_state(user, not user["forwarding"])


settings_window = Window(
    Multi(
        Const("Forwarding state:"),
        Case(
            {True: Const("enabled"), False: Const("disabled")},
            selector=lambda d, *x: d['dialog_data']['user']['forwarding']
            # change to F["dialog_data"]["user"]["forwarding"] when it is fixed in library
        ),
        sep=" ",
    ),
    Const(
        "\n" \
            "<b>Attention!</b> \n"\
            "Message forwarding is paused when this menu is opened."
        ),
    Format(
        "\n" \
            "✉ You have {dialog_data[user][msgs_queue_len]} forwarded messages in the queue. \n" \
             "Close the menu to see them.",
        when=F["dialog_data"]["user"]["msgs_queue_len"] > -1
    ),
    Button(
        text=Case(
                {
                    True: Const("Disable message forwarding"),
                    False: Const("Enable message forwarding")
                },
                selector=lambda d, *x: d['dialog_data']['user']['forwarding']
                # change to F["dialog_data"]["user"]["forwarding"] when it is fixed in library
        ),
        on_click=on_forwarding_toggle_click,
        id="forwarding_toggle",
    ),
    SwitchTo(
        text=Const("Manage keywords"),
        id="manage_keywords_btn",
        state=SettingsSG.manage_keywords,
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
        await bf.add_keyword(user, message.text.strip())
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
        List(Format("  - {item}"), items=lambda d: d["dialog_data"]["user"]["keywords"]),
        when=F["dialog_data"]["user"]["keywords"].len() > 0,
        sep="\n",
    ),

    Const(
        "\n" \
            "<b>Attention!</b> \n" \
            "The amount of keywords in your list is limited by 10. \n" \
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
        await bf.remove_keyword(user, item_id)


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
            items='keywords',
            item_id_getter=lambda a: a,
            on_click=on_remove_kw_selected,
        ),
        width=2,
        when=F["dialog_data"]["user"]["keywords"].len() > 0,
    ),
    SwitchTo(text=Const("Back"), id="manage_keywords_btn", state=SettingsSG.manage_keywords),
    state=SettingsSG.remove_keyword,
)


# ======================================================================================================
# Processing subdialog results

async def process_result(start_data: Data, result: Any, manager: DialogManager):
    """
    Called when subdialog is finished.
    Just show the main menu as a new message.
    """
    manager.show_mode = ShowMode.SEND
    await manager.done()


# ======================================================================================================
# Dialog object

async def on_dialog_close(ddd: Any, manager: DialogManager):
    pass
    


dialog = Dialog(
    settings_window,
    manage_keywords_window,
    remove_keyword_window,
    on_process_result=process_result,
    getter=data_getter,
    on_close=on_dialog_close
)
