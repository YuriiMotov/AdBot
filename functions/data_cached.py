from datetime import datetime, timedelta
from typing import Any, Optional, TypeAlias, Union
from collections.abc import Awaitable, Callable

from sqlalchemy.orm import Session, load_only, with_expression, selectinload
from sqlalchemy import select, func 

from db import models as m

UserDict: TypeAlias = dict[str, Union[bool, str, int, float, list[int | str]]]
ForwardFunc: TypeAlias = Callable[[int, str], Awaitable[bool]]


class DataCached():
    def __init__(self):
        self._users_cache = None
        self._keywords_cache = None
        self._keywords_update_required = True


    def _user_to_dict(self, user: m.User) -> UserDict:
        return {
            'id': user.id,
            'keywords_limit': 10,
            'last_activity_dt': datetime.now().timestamp(),
            'forwarding': user.forwarding,
            'keywords': [kw.word for kw in user.keywords],
            'menu_closed': user.menu_closed,
            'msgs_queue_len': user.forward_queue_len,
        }

    async def refresh_user_data(self, session: Session, user_id: int) -> None:
        """
            Refresh data that can be changed by others.
            It affetcts only one user.
        """
        if self._users_cache is None:
            self._load_users_data(session)

        st = select(m.User) \
            .outerjoin_from(m.User, m.user_message_link).group_by(m.User.id) \
            .where(m.User.id == user_id) \
            .options(
                load_only(m.User.id),
                with_expression(m.User.forward_queue_len, func.count(m.user_message_link.c.user_id))
            )

        user = session.scalar(st)
        if user:
            user_data = self._users_cache[user.id]
            user_data["msgs_queue_len"] = user.forward_queue_len



    async def refresh_users_data(self, session: Session) -> list[int]:
        """
            Refresh data that can be changed by others.
            It affetcts all the active users (menu is open).
            Returns a list of ids of active users
        """
        if self._users_cache is None:
            self._load_users_data(session)

        st = select(m.User) \
            .outerjoin_from(m.User, m.user_message_link).group_by(m.User.id) \
            .where(m.User.menu_closed == False) \
            .options(
                load_only(m.User.id),
                with_expression(m.User.forward_queue_len, func.count(m.user_message_link.c.user_id))
            )

        time_point = (datetime.now() - timedelta(minutes=2)).timestamp()
        ids = []
        for user in session.scalars(st).all():
            user_data = self._users_cache[user.id]
            if (user_data['last_activity_dt'] >= time_point):
                user_data["msgs_queue_len"] = user.forward_queue_len
                ids.append(user.id)
        return ids


    def _load_users_data(self, session: Session) -> None:
        if self._users_cache is None:
            st = select(m.User) \
                    .outerjoin_from(m.User, m.user_message_link).group_by(m.User.id) \
                    .where(m.User.menu_closed == False) \
                    .options(
                        selectinload(m.User.keywords),
                        with_expression(m.User.forward_queue_len, func.count(m.user_message_link.c.user_id))
                    )
            users = session.scalars(st).all()
            self._users_cache = {user.id: self._user_to_dict(user) for user in users}


    def _load_user_data(self, session: Session, user_id: int) -> None:
        if self._users_cache is not None:
            st = select(m.User) \
                    .outerjoin_from(m.User, m.user_message_link).group_by(m.User.id) \
                    .where(m.User.id == user_id) \
                    .options(
                        selectinload(m.User.keywords),
                        with_expression(m.User.forward_queue_len, func.count(m.user_message_link.c.user_id))
                    )
            user = session.scalar(st)
            if user is not None:
                self._users_cache[user_id] = self._user_to_dict(user)


    async def get_user_data(self, session: Session, user_id: int) -> Optional[UserDict]:
        if self._users_cache is None:
            self._load_users_data(session)
        if user_id not in self._users_cache:
            self._load_user_data(session, user_id)
        user_data = self._users_cache.get(user_id)
        return user_data


    async def add_user(self, session: Session, user_id: int, user_name: str) -> Optional[UserDict]:
        user = m.User()
        user.id = user_id
        user.telegram_name = user_name
        user.forward_queue_len = 0
        session.add(user)
        session.commit()
        return await self.get_user_data(session, user_id)


    async def set_forwarding_state(self, session: Session, user_id: int, new_state: bool) -> UserDict:
        user_data = await self.get_user_data(session, user_id)
        user_data['last_activity_dt'] = datetime.now().timestamp()
        user = session.get(m.User, user_id)
        user.forwarding = new_state
        user_data['forwarding'] = new_state
        session.commit()
        self._keywords_update_required = True
        return user_data


    async def set_menu_closed_state(self, session: Session, user_id: int, new_state: bool) -> None:
        user_data = await self.get_user_data(session, user_id)
        user = session.get(m.User, user_id)
        if user:
            user.menu_closed = new_state
            user_data['menu_closed'] = new_state
            session.commit()
    

    async def get_menu_closed_state(self, session: Session, user_id: int) -> bool:
        user_data = await self.get_user_data(session, user_id)
        if user_data:
            return user_data['menu_closed']
        else:
            return True
    

    async def reset_inactivity_timer(self, session: Session, user_id: int) -> None:
        user_data = await self.get_user_data(session, user_id)
        if user_data:
            user_data['last_activity_dt'] = datetime.now().timestamp()
        

    async def get_inactive_users(self, session: Session) -> list[int]:
        if self._users_cache is None:
            self._load_users_data(session)
        time_point = (datetime.now() - timedelta(minutes=2)).timestamp()
        return [
            user['id'] for user in self._users_cache.values() \
                if ((not user['menu_closed']) and (user['last_activity_dt'] < time_point))
        ]


    async def get_active_users(self, session: Session) -> None:
        if self._users_cache is None:
            self._load_users_data(session)
        time_point = (datetime.now() - timedelta(minutes=2)).timestamp()
        return [
            user['id'] for user in self._users_cache.values() \
                if ((not user['menu_closed']) and (user['last_activity_dt'] >= time_point))
        ]


    async def process_groupchat_messages(self, session: Session) -> None:
        keywords = self.get_all_keywords(session)
        #To Do: preload users
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


    async def forward_msgs(self, session: Session, forward_func: ForwardFunc) -> None:
        st = select(m.User).where(m.User.forwarding == True).options(selectinload(m.User.forward_queue))
        users = session.scalars(st).all()
        for user in users:
            for msg in user.forward_queue:
                if await self.get_menu_closed_state(session, user.id):
                    await forward_func(user.id, msg.url)
                    user.forward_queue.remove(msg)
        session.commit()


    # Keywords managment

    async def add_keyword(self, session: Session, user_id: int, keyword: str) -> UserDict:
        user_data = await self.get_user_data(session, user_id)
        user_data['last_activity_dt'] = datetime.now().timestamp()
        keyword = keyword.lower().strip()
        if len(user_data["keywords"]) < user_data['keywords_limit']:
            if keyword not in user_data['keywords']:
                st = select(m.Keyword).where(m.Keyword.word == keyword)
                kw = session.scalars(st).one_or_none()
                if kw is None:
                    kw = m.Keyword(word=keyword)
                st = select(m.User).where(m.User.id == user_id).options(
                    selectinload(m.User.keywords),
                    load_only(m.User.id)
                )
                user = session.scalar(st)
                user.keywords.append(kw)
                user_data['keywords'].append(keyword)
                self._keywords_update_required = True
            session.commit()
        return user_data


    async def remove_keyword(self, session: Session, user_id: int, keyword: str) -> UserDict:
        user_data = await self.get_user_data(session, user_id)
        user_data['last_activity_dt'] = datetime.now().timestamp()
        st = select(m.Keyword).where(m.Keyword.word == keyword)
        kw = session.scalars(st).one_or_none()
        if kw is not None:
            st = select(m.User).where(m.User.id == user_id).options(
                selectinload(m.User.keywords),
                load_only(m.User.id)
            )
            user = session.scalar(st)
            if kw in user.keywords:
                user.keywords.remove(kw)
                if keyword in user_data['keywords']:
                    user_data['keywords'].remove(keyword)
                session.commit()
                self._keywords_update_required = True
        return user_data


    def get_all_keywords(self, session: Session):
        if self._keywords_update_required:
            self._keywords_cache = {}
            st = select(m.Keyword) \
                    .join_from(m.Keyword, m.user_keyword_link) \
                    .join_from(m.user_keyword_link, m.User) \
                    .where(m.User.forwarding == True) \
                    .group_by(m.Keyword.id) \
                    .options(
                        selectinload(m.Keyword.users).options(load_only(m.User.id))
                    )
            for kw in session.scalars(st).all():
                self._keywords_cache[kw.word] = [user.id for user in kw.users]
            self._update_required = False
        return self._keywords_cache
    
