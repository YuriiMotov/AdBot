from typing import Awaitable
import aiohttp

#from aiogram.types import Message
from sqlalchemy.orm import Session
from hashlib import md5

from db.models import GroupChatMessage


async def get_telegram_updates():
    session: aiohttp.ClientSession

    with aiohttp.ClientSession() as session:
        async with session.get('http://python.org') as response:
            if response.status == 200:
                await process_events()
            else:
                print('Userbot error: error requesting updates')
            


async def add_groupchat_msg(session: Session, message: dict) -> Awaitable:
    chat_msg = GroupChatMessage()
    # chat_msg.url = message.get_url()
    # chat_msg.text = message.text
    # chat_msg.text_hash = md5(message.text, usedforsecurity=False).hexdigest()
    session.add(chat_msg)


async def process_events():
    pass