from typing import Awaitable, Optional, Coroutine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import select

from .session_decorator import add_session
from db import models as m



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
async def filter_messages(session: Session, user_id: int) -> None:
    pass


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

    user = session.get(m.User, user_data['id'])
    if len(user.keywords) < user_data['keywords_limit']:
        st = select(m.Keyword).where(m.Keyword.word == keyword)
        kw = session.scalars(st).one_or_none()
        if kw is None:
            kw = m.Keyword(word=keyword)
        
        if kw not in user.keywords:
            user.keywords.append(kw)

        session.add_all([user, kw])
        session.commit()

        # TODO: Add error handling
        
        user_to_dict(user, user_data)




@add_session
async def remove_keyword(session: Session, user_data: dict, keyword: str) -> None:
    
    st = select(m.Keyword).where(m.Keyword.word == keyword)
    kw = session.scalars(st).one_or_none()
    if kw is not None:
    
        user = session.get(m.User, user_data['id'])
        user.keywords.remove(kw)

        # session.add_all([user, kw])
        session.commit()

    # TODO: Add error handling
    
    user_to_dict(user, user_data)


@add_session
async def set_forwarding_state(session: Session, user_data: dict, frwrd_state: bool) -> None:
    
    print('Set forwarding state is called')

    user = session.get(m.User, user_data['id'])
    user.forwarding = frwrd_state
    session.commit()

    user_to_dict(user, user_data)
