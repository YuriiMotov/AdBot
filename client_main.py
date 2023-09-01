import asyncio
import logging

from telethon import TelegramClient
from telethon.tl.types import Message
from telethon.tl.custom.dialog import Dialog

from config_reader import config
from functions import userbot_functions as ubf

logger = logging.getLogger(__name__)

MAX_DIALOG_HISTORY_MESSAGES_CNT = 500
CHECK_NEW_MESSAGES_INTERVAL = 300

client = None


async def check_new_messages_stub():
    logger.debug('check_new_messages_stub')


async def check_new_messages():
    logger.debug('check_new_messages started')
    async with client:

        dialog: Dialog
        message: Message

        # Iterate through chats and messages, add messages to DB
        async for dialog in client.iter_dialogs():
            if dialog.is_channel or dialog.is_group:
                if hasattr(dialog, "name"):
                    logger.debug(f"check_new_messages parse chat '{dialog.name}'. Unreaded: {dialog.unread_count}")
                else:
                    logger.debug(f"check_new_messages parse chat '??' (doesn't have `name` attr)")

                unread_cnt = min(dialog.unread_count, MAX_DIALOG_HISTORY_MESSAGES_CNT)
                if dialog.unread_count > unread_cnt:
                    skipped = (dialog.unread_count - unread_cnt)
                    logger.warning(f'check_new_messages skipped {skipped} msgs')


                max_msg_id = 0
                my_chat = await client.get_entity(dialog)

                async for message in client.iter_messages(dialog, unread_cnt):
                    if hasattr(message, 'from_id') and message.from_id:
                        sender = await client.get_entity(message.from_id)
                        if message.message and hasattr(sender, 'bot') and not sender.bot:
                            try:
                                if hasattr(my_chat, 'username') and my_chat.username:
                                    link = f'https://t.me/{my_chat.username}/{message.id}'
                                else:
                                    link = f'https://t.me/c/{my_chat.id}/{message.id}'
                                await ubf.add_groupchat_msg(message.message, link)
                            except Exception as e:
                                print(f'Error in client: {e} during processing `{message.message[:150]}`')

                            max_msg_id = max(max_msg_id, message.id)
                        await asyncio.sleep(0.1)

                if max_msg_id > 0:
                    await client.send_read_acknowledge(my_chat, max_id=max_msg_id)

        # ToDo: check if the total time less than (CHECK_NEW_MESSAGES_INTERVAL / 2)
    logger.debug('check_new_messages finished')


if config.TEST == 1:
    check_new_messages = check_new_messages_stub
    logger.debug('TEST == 1')
else:
    client = TelegramClient(
        'telethon.session',
        config.API_ID,
        config.API_HASH.get_secret_value(),
        system_version="4.16.30-vxCUSTOM",
        retry_delay=3
    )
    logger.debug('Telethon client object created')

