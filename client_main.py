import asyncio

from telethon import TelegramClient
from telethon.tl.types import Message
from telethon.tl.custom.dialog import Dialog

from config_reader import config
from functions import userbot_functions as ubf

MAX_DIALOG_HISTORY_MESSAGES_CNT = 500
CHECK_NEW_MESSAGES_INTERVAL = 300

client = None


async def check_new_messages_stub():
    print('check_new_messages_stub')


async def check_new_messages():

    async with client:

        # me = await client.get_me()

        dialog: Dialog
        message: Message

        # Iterate through chats and messages, add messages to DB
        async for dialog in client.iter_dialogs():
            if dialog.is_channel or dialog.is_group:
                unread_cnt = min(dialog.unread_count, MAX_DIALOG_HISTORY_MESSAGES_CNT)

                max_msg_id = 0
                my_chat = await client.get_entity(dialog)

                async for message in client.iter_messages(dialog, unread_cnt):
                    if hasattr(message, 'from_id') and message.from_id:
                        sender = await client.get_entity(message.from_id)
                        if message.message and not sender.bot:
                            if hasattr(my_chat, 'username') and my_chat.username:
                                link = f'https://t.me/{my_chat.username}/{message.id}'
                            else:
                                link = f'https://t.me/c/{my_chat.id}/{message.id}'
                            await ubf.add_groupchat_msg(message.message, link)

                            max_msg_id = max(max_msg_id, message.id)
                        await asyncio.sleep(0.1)

                if max_msg_id > 0:
                    await client.send_read_acknowledge(my_chat, max_id=max_msg_id)

        # ToDo: check if the total time less than (CHECK_NEW_MESSAGES_INTERVAL / 2)


if config.TEST == 1:
    check_new_messages = check_new_messages_stub
else:
    client = TelegramClient(
        'telethon.session',
        config.API_ID,
        config.API_HASH.get_secret_value(),
        system_version="4.16.30-vxCUSTOM",
        retry_delay=3
    )
