from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, insert
from aiogram import Bot

from .session_decorator import add_session
from db import models as m
from .keywords_cache import keywords_cached

bot: Bot = None


def user_to_dict(user: m.User, user_dict: Optional[dict] = None) -> dict:
    if user_dict is None:
        user_dict = {}   
    user_dict['id'] = user.id
    user_dict['forwarding'] = user.forwarding
    user_dict['keywords'] = [kw.word for kw in user.keywords]
    user_dict['keywords_limit'] = 10
    user_dict['msgs_queue_len'] = len(user.forward_queue)
    return user_dict


@add_session
async def get_user(session: Session, user_id: int) -> Optional[dict]:
    user = session.get(m.User, user_id)
    if user:
        return user_to_dict(user)
    else:
        return None


@add_session
async def add_user(session: Session, user_id: int, user_name: str) -> Optional[dict]:
    user = m.User()
    user.id = user_id
    user.telegram_name = user_name
    session.add(user)
    session.commit()
    # TODO: Add error handling  
    return user_to_dict(user)


@add_session
async def add_keyword(session: Session, user_data: dict, keyword: str) -> None:
    keyword = keyword.lower().strip()
    user = session.get(m.User, user_data['id'])
    if len(user.keywords) < user_data['keywords_limit']:
        st = select(m.Keyword).where(m.Keyword.word == keyword)
        kw = session.scalars(st).one_or_none()
        if kw is None:
            kw = m.Keyword(word=keyword)
        if kw not in user.keywords:
            user.keywords.append(kw)
            keywords_cached.request_update()
        session.add_all([user, kw])
        session.commit()
        # TODO: Add error handling
        user_to_dict(user, user_data)


@add_session
async def remove_keyword(session: Session, user_data: dict, keyword: str) -> None:
    # TODO: Add error handling
    st = select(m.Keyword).where(m.Keyword.word == keyword)
    kw = session.scalars(st).one_or_none()
    if kw is not None:
        user = session.get(m.User, user_data['id'])
        if kw in user.keywords:
            user.keywords.remove(kw)
            # session.add_all([user, kw])
            session.commit()
            keywords_cached.request_update()
            user_to_dict(user, user_data)


@add_session
async def set_forwarding_state(session: Session, user_data: dict, frwrd_state: bool) -> None:
    user = session.get(m.User, user_data['id'])
    user.forwarding = frwrd_state
    session.commit()
    keywords_cached.request_update()
    user_to_dict(user, user_data)


# Scheduler tasks

@add_session
async def forward_messages(session: Session) -> None:
    st = select(m.User).where(m.User.forwarding == True).where(m.User.menu_closed == True)
    users = session.scalars(st).all()
    for user in users:
        for msg in user.forward_queue:
            await bot.send_message(
                        chat_id=user.id,
                        text=f'{msg.text}\n{msg.url}',
                        disable_notification=True
            )
            msg_short = msg.text[:20].replace('\n', '')
            print(f"Sended message: '{msg_short}' to user {user.id}")
            user.forward_queue.remove(msg)
    session.commit()
        

@add_session
async def process_groupchat_messages(session: Session):
    keywords = keywords_cached.get_keywords(session)
    st = select(m.GroupChatMessage).where(m.GroupChatMessage.processed == False)
    msgs = session.scalars(st).all()
    for msg in msgs:
        msg_text = msg.text.lower()
        for kw, user_ids in keywords.items():
            if kw in msg_text:
                for user_id in user_ids:
                    user = session.get(m.User, user_id)
                    user.forward_queue.append(msg)
        msg.processed = True
    session.commit()
