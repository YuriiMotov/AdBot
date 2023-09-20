"""
    To use these tests you have to:
     - create test bot
     - create test group and find out the id of that group (try to copy link of message
        from that group and look at the number in the link,
        i.e. http://t.me/c/111111/22.Here 111111 is a chat id)
     - add test bot to test group with the admin rights. Turn off the 'group privacy'
        option of the bot
     - add to config:
        - MODE='TEST'
        - CHATS_FILTER='test_chat_id'
        - TESTBOT_NAME='your_test_bot_name'
        - CLIENT_ID=123321123
    
    If you don't know your client user id, just run tests, they will fail and you can see
    the right client id in the error message.

"""

import asyncio
import pytest

from sqlalchemy import select, text
from sqlalchemy.orm import Session
from telethon import TelegramClient
from telethon.tl.custom.conversation import Conversation
from telethon.tl.custom.message import Message, MessageButton

from adbot.domain import models

from conftest import (
    E2E_Env, client_send_to_bot, client_get_from_bot, client_send_to_test_chat,
    client_get_my_id
)


@pytest.mark.asyncio
async def test_correct_client_id(e2e_env: E2E_Env):
    client_id = await client_get_my_id(e2e_env.client)

    # If it fails, just take right client_id and specify it in config file
    assert client_id == e2e_env.client_id


@pytest.mark.asyncio
async def test_full_msg_forwarding_cycle(e2e_env: E2E_Env):
    
    app_task = asyncio.create_task(e2e_env.app.run())

    ad_bot_srv = e2e_env.app._ad_bot_services
    user = await ad_bot_srv.create_user_by_telegram_data(e2e_env.client_id, '')
    await ad_bot_srv.set_subscription_state(user.id, True)
    await ad_bot_srv.add_keyword(user.id, 'monitor')

    await client_send_to_test_chat(e2e_env.client, e2e_env.test_chat_id, 'I`m selling the monitor HP')
    await asyncio.sleep(0.5)

    await e2e_env.app.fetch_messages()
    await asyncio.sleep(0.5)

    await e2e_env.app._ad_bot_services.resume_loop()
    with ad_bot_srv._db_pool() as session:
        session: Session
        msg = session.scalar(select(models.GroupChatMessage).limit(1))
        assert msg is not None
        assert msg.processed == True

    await asyncio.sleep(0.5)

    message = await client_get_from_bot(e2e_env.client, e2e_env.bot_name)

    assert message.text.find('t.me') >= 0

    await e2e_env.app._ad_bot_services.stop()

    c = 20
    while c and (not app_task.done()):
        await asyncio.sleep(0.5)
        c -= 1
    
