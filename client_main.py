import asyncio

from telethon import TelegramClient
from telethon.tl.types import Message
from telethon.tl.custom.dialog import Dialog

from config_reader import config
from functions import userbot_functions as ubf

MAX_DIALOG_HISTORY_MESSAGES_CNT = 10
CHECK_NEW_MESSAGES_INTERVAL = 300

client = TelegramClient('telethon.session', config.API_ID, config.API_HASH.get_secret_value())


async def request_sms_code() -> str:
    # Send message to admin via telegram bot:
    # ask to check the SMS and forward code or follow the link inside to authorize userbot client
    print('SMS code requested. Send message to admin and wait 1 minute')
    # ToDo: send message via bot
    sms_code = ''
    await asyncio.sleep(60)
    return sms_code


async def check_new_messages():

    async with client:

        # Get list of dialogs
        dialogs = await client.iter_dialogs()

        dialog: Dialog
        message: Message

        # Iterate through chats and messages, add messages to DB
        async for dialog in dialogs:
            if dialog.is_channel or dialog.is_group:
                unread_cnt = min(dialog.unread_count, MAX_DIALOG_HISTORY_MESSAGES_CNT)
                async for message in client.iter_messages(dialog, unread_cnt):
                    await ubf.add_groupchat_msg(message.message, f'{dialog.id}/{message.id}')
                    await asyncio.sleep(0.1)
           
        # ToDo: check if the total time less than (CHECK_NEW_MESSAGES_INTERVAL / 2)


async def main():

    # start client first time to check whether it is authorized and authorize if it is needed
    client.start(phone=config.PHONE, code_callback=request_sms_code)

    while True:     # ToDo: add exit condition?
        await check_new_messages()
        asyncio.sleep(CHECK_NEW_MESSAGES_INTERVAL)




if __name__ == '__main__':
    asyncio.run(main)