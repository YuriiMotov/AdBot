from typing import Any

from aiogram.filters.state import StatesGroup, State
from aiogram.types import Message, CallbackQuery
from aiogram_dialog import (
    Window,
    DialogManager,

)
from aiogram_dialog.widgets.kbd import Cancel, Back, Next
from aiogram_dialog.widgets.text import Const, Jinja
from aiogram_dialog import Dialog
from aiogram_dialog.widgets.input import MessageInput

from functions import bot_functions as bf
from dialogs.common import (
    data_getter, on_unexpected_input
)


# ======================================================================================================
# Settings dialog's states

class HelpSG(StatesGroup):
    main = State()
    chats_list = State()
    dialog_closed = State()


# ======================================================================================================
# Main help window

# help_html_text = Jinja(
# """
# This bot was disigned to help people track ads in russian-language Montenegro's telegram chats.

# For example, you want to by bicycle. You can set keyword 'велосипед' (and don't forget to <u>enable forwarding</u>).
# After that bot will forward all the messages that contain the word 'велосипед' to you.
# So, you don't have to spend time reading millions of messages in those chats.

# This is an opensource project. You can setup it on your server and adjust it for your own needs.

# You can find more information at the project page on GIT: <a href="https://github.com/YuriiMotov/AdBot#readme">AdBot</a>

# To open settings menu type /menu or choose this item in the bot menu (in the bottom-left corner of the app).
                       
# """
# )


help_html_text = Jinja(
"""
This bot was disigned to help people track ads in russian-language Montenegro's telegram chats.

For example, you want to buy bicycle. You can set keyword 'велосипед' (and don't forget to <u>enable forwarding</u>).
After that bot will forward all the messages that contain the word 'велосипед' to you.
So, you don't have to spend time reading millions of messages in those chats.

To <b><u>open settings menu</u></b> type /menu or choose this item in the bot menu (in the bottom-left corner of the app).

<b><u>Add your keywords</u></b> by clicking 'Manage keywords' and typing keywords one by one in the chat.

If you need to <b><u>delete keyword</u></b> from the list, click 'Remove keyword' and click the button with the keyword you want to delete from the list.

After you created the list of keywords, <b><u>return back</u></b> to main menu (click `Back`) and <b><u>enable Forwarding</u></b> by clicking button 'Enable forwarding'. You will see status 'Forwarding state: Enabled' on the top of the message.

That's it. Since that moment bot will forward to you all the messages from followed chats that contain your keywords.

To <b><u>see list of followed chats</u></b>, click the button 'List of chats' below.

                       
"""
)

main_help_window = Window(
    Const("<b>Help</b>"),
    help_html_text,
    Next(text=Const('List of chats')),
    Cancel(text=Const("Close")),
    MessageInput(on_unexpected_input),
    getter=data_getter,
    disable_web_page_preview=True,
    state=HelpSG.main,
)



# ======================================================================================================
# `List of chats` window



chat_list_html_text = Jinja(
"""
 * <a href="https://t.me/sale_me_com">Черногория Объявления | Барахолка | Доска объявлений</a>
 * <a href="https://t.me/montenegro_market">ЧЕРНОГОРИЯ | барахолка объявления чат</a>
 * <a href="https://t.me/loveBar1">Черногория Бар | Услуги | Барахолка</a>
 * <a href="https://t.me/mtl_fair">Барахолка Монтелиберо</a>
 * <a href="https://t.me/SpecialistsMontenegro">Черногория Специалисты</a>
 * <a href="https://t.me/Montenegrospecialist">Специалисты Черногория</a>
 * <a href="https://t.me/monteworkers">Работа в Черногории </a>

                       
"""
)

chats_list_help_window = Window(
    Const("<b>This bot follows next telegram chats:</b>"),
    chat_list_html_text,
    Back(text=Const('Back')),
    Cancel(text=Const("Close")),
    MessageInput(on_unexpected_input),
    getter=data_getter,
    disable_web_page_preview=True,
    state=HelpSG.chats_list,

)




# ======================================================================================================
# Dialog closed window

dialog_closed_window = Window(
    Const("..."),
    state=HelpSG.dialog_closed,
)


# ======================================================================================================
# Dialog object

async def on_dialog_close(result: Any, manager: DialogManager):
    await bf.set_menu_closed_state(manager.event.from_user.id, True)
    event = manager.event
    if isinstance(event, CallbackQuery):
        await event.message.delete()
    elif isinstance(event, Message):
        await manager.switch_to(HelpSG.dialog_closed)
        await manager.show()     

 
dialog = Dialog(
    main_help_window,
    chats_list_help_window,
    dialog_closed_window,
    on_close=on_dialog_close
)
