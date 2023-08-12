from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
import logging
from typing import Any, Optional, TypeAlias, Union

from sqlalchemy.orm import Session, load_only, with_expression, selectinload
from sqlalchemy import select, delete, func
from sqlalchemy.exc import SQLAlchemyError

from db import models as m

UserDict: TypeAlias = dict[str, Union[bool, str, int, float, list[int | str]]]
ForwardFunc: TypeAlias = Callable[[int, str], Awaitable[bool]]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class DataCached():
    def __init__(self):
        self._users_cache = None
        self._keywords_cache = None
        self._keywords_update_required = True


    def _db_error_handle(self, error: SQLAlchemyError) -> None:
        # if isinstance(error, OperationalError):
        #     pass

        logger.error(f'Exception {error.__class__} {error}')


    def _user_to_dict(self, user: m.User) -> UserDict:
        """
            Pack user data from DB object to dict.
            Returns `UserDict` or raise `SQLAlchemyError`.
        """
        return {
            'id': user.id,
            'keywords_limit': 10,
            'last_activity_dt': datetime.now().timestamp(),
            'forwarding': user.forwarding,
            'keywords': [kw.word for kw in user.keywords],
            'menu_closed': user.menu_closed,
            'msgs_queue_len': user.forward_queue_len,
        }


    async def refresh_user_data(self, session: Session, user_id: int) -> bool:
        """
            Refresh data that can be changed by others.
            This method affetcts only one user with id = user_id.
            Returns `True` on success and `False` on DB error.
        """
        user_data = await self.get_user_data(session, user_id)
        if user_data:
            try:
                st = select(m.User) \
                        .outerjoin_from(m.User, m.user_message_link).group_by(m.User.id) \
                        .where(m.User.id == user_id) \
                        .options(
                            load_only(m.User.id),
                            with_expression(
                                m.User.forward_queue_len,
                                func.count(m.user_message_link.c.user_id)
                            )
                        )
                user = session.scalar(st)
                if user:
                    user_data["msgs_queue_len"] = user.forward_queue_len
                    return True
            except SQLAlchemyError as e:
                self._db_error_handle(e)
        return False    # DB Error or user doesn't exist


    async def refresh_users_data(self, session: Session) -> list[int]:
        """
            Refresh data that can be changed by others.
            This method affetcts all the active users (menu_closed == False).
            Returns a list of ids of active users.
        """
        if not self._load_active_users_data(session):
            return []   # DB Error
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
            user_data = self._users_cache.get(user.id)
            if user_data and (user_data['last_activity_dt'] >= time_point):
                user_data["msgs_queue_len"] = user.forward_queue_len
                ids.append(user.id)
        return ids


    def _load_active_users_data(self, session: Session) -> bool:
        """
            Load user data to `_users_cache` dict (only if `_users_cache dict` is None)
            for all active users (`menu_closed` == False).
            Returns `True` on success or `False` on DB error.
        """
        if self._users_cache is None:
            try:
                st = select(m.User) \
                        .outerjoin_from(m.User, m.user_message_link).group_by(m.User.id) \
                        .where(m.User.menu_closed == False) \
                        .options(
                            selectinload(m.User.keywords),
                            with_expression(m.User.forward_queue_len, func.count(m.user_message_link.c.user_id))
                        )
                users = session.scalars(st).all()
                self._users_cache = {user.id: self._user_to_dict(user) for user in users}
            except SQLAlchemyError as e:
                self._db_error_handle(e)
                return False    # DB Error
        return True


    def _load_user_data(self, session: Session, user_id: int) -> bool:
        """
            Load user data to `_users_cache` dict for user with id = user_id.
            Returns:
                `True` on success
                `False` on DB error or if `_users_cache` is None
        """
        if self._users_cache is not None:
            try:
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
                    return True
            except SQLAlchemyError as e:
                self._db_error_handle(e)
        return False # DB Error or method `_load_active_users_data` wasn't called before


    async def get_user_data(self, session: Session, user_id: int) -> Optional[UserDict]:
        """
            If user with id = user_id isn't exist in cache, load user data to `_users_cache` dict.
            Returns:
                `UserDict` dict on success
                `None` on DB error
        """
        if self._load_active_users_data(session):
            if user_id not in self._users_cache:
                if not self._load_user_data(session, user_id):
                    return None # DB Error or user doesn't exist
            user_data = self._users_cache.get(user_id)
            return user_data
        return None # DB Error


    async def add_user(self, session: Session, user_id: int, user_name: str) -> Optional[UserDict]:
        """
            Add user to DB.
            Returns:
                `UserDict` dict on success
                `None` on DB error
        """        
        user = m.User()
        user.id = user_id
        user.telegram_name = user_name
        user.forward_queue_len = 0
        try:
            session.add(user)
            session.commit()
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            return None     # DB error
        return await self.get_user_data(session, user_id)   # `UserDict` or `None`


    async def set_forwarding_state(self, session: Session, user_id: int, new_state: bool) -> bool:
        """
            Set `forwarding` attribute of user to `new_state`.
            Update data in DB and in cache.
            Set `_keywords_update_required` to True (need to update keywords cache).
            BTW update `last_activity_dt`.
            Returns:
                `True` on success
                `False` on DB error
        """
        user_data = await self.get_user_data(session, user_id)
        if user_data:
            user_data['last_activity_dt'] = datetime.now().timestamp()
            self._keywords_update_required = True
            try:
                user = session.get(m.User, user_id)
                user.forwarding = new_state
                session.commit()
                user_data['forwarding'] = new_state
                return True
            except SQLAlchemyError as e:
                self._db_error_handle(e)
        return False     # DB error


    async def set_menu_closed_state(self, session: Session, user_id: int, new_state: bool) -> bool:
        """
            Set `menu_closed` attribute of user to `new_state`.
            Update data in DB and in cache.
            Returns:
                `True` on success
                `False` on DB error
        """
        user_data = await self.get_user_data(session, user_id)
        if user_data:
            try:
                user = session.get(m.User, user_id)
                user.menu_closed = new_state
                session.commit()
                user_data['menu_closed'] = new_state
                return True
            except SQLAlchemyError as e:
                self._db_error_handle(e)
        return False     # DB error


    async def get_menu_closed_state(self, session: Session, user_id: int) -> Optional[bool]:
        """
            Get `menu_closed` attribute of user.
            Returns `menu_closed` attribute state or `None` on DB error 
        """
        if self._load_active_users_data(session):
            if user_id in self._users_cache:
                return self._users_cache[user_id]['menu_closed']    # Return state
            else:           # If user data not in cache, it means that this user is inactive
                return True # (`menu_closed` == True)
        else:
            return None     # DB error
    

    async def reset_inactivity_timer(self, session: Session, user_id: int) -> bool:
        """
            Set `last_activity_dt` to current date and time.
            Also set `menu_closed` state to `False`.
            Returns `True` on success and `False` on DB error.
        """
        user_data = await self.get_user_data(session, user_id)
        if user_data:
            user_data['last_activity_dt'] = datetime.now().timestamp()
            if user_data['menu_closed']:
                if await self.set_menu_closed_state(session, user_id, False):
                    return True
                else:
                    return False    # DB error during set_menu_closed_state execution
            else:
                return True
        else:
            return False    # DB error
        

    async def get_inactive_users(self, session: Session) -> Optional[list[int]]:
        """
            Get list of inactive users' ids (menu is opened, but not actions
            performed during last XX sec).
            Returns list of ids or None on DB error.
        """
        if self._load_active_users_data(session):
            time_point = (datetime.now() - timedelta(minutes=2)).timestamp()
            return [
                user_data['id'] for user_data in self._users_cache.values() \
                    if (
                        (not user_data['menu_closed'])
                        and 
                        (user_data['last_activity_dt'] < time_point)
                    )
            ]
        else:
            return None     # DB error

    # It isn't used. Remove?
    #
    # async def get_active_users(self, session: Session) -> None:
    #     if self._users_cache is None:
    #         self._load_active_users_data(session)
    #     time_point = (datetime.now() - timedelta(minutes=2)).timestamp()
    #     return [
    #         user['id'] for user in self._users_cache.values() \
    #             if ((not user['menu_closed']) and (user['last_activity_dt'] >= time_point))
    #     ]


    async def process_groupchat_messages(self, session: Session) -> bool:
        """
            Process unprocessed messages, add them to the users' queues according to their keywords.
            Returns `True` on success or `False` on DB error.
        """
        keywords = self.get_all_keywords(session)
        if keywords is None:
            return False    # DB error
        # # Cache user data in session
        # users_ids = set()
        # for uids in keywords.values():
        #     users_ids.update(uids)
        # st = select(m.User).where(m.User.id.in_(users_ids)).options(
        #         # load_only(m.User.id),
        #         selectinload(m.User.forward_queue)
        #     )
        # session.execute(st)
        try:
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
            return True     # Success
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            return False    # DB error


    async def forward_msgs(self, session: Session, forward_func: ForwardFunc) -> bool:
        """
            Process messages in users' queues, call `forward_func` for each of them.
            Returns `True` on success or `False` on DB error.
        """
        try:
            st = select(m.User).where(m.User.forwarding == True).options(selectinload(m.User.forward_queue))
            users = session.scalars(st).all()
            for user in users:
                for msg in user.forward_queue:
                    if (await self.get_menu_closed_state(session, user.id)) == True:
                        if await forward_func(user.id, msg.url):
                            user.forward_queue.remove(msg)
            session.commit()
            return True
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            return False    # DB error


    #===============================================================================
    # Keywords managment

    async def add_keyword(self, session: Session, user_id: int, keyword: str) -> bool:
        """
            Add keyword to user in DB and to cached user data.
            Also set `_keywords_update_required` to True (need update keywords cache).
            Also update `last_activity_dt`.
            Returns `True` on success or `False` on DB error.
        """
        user_data = await self.get_user_data(session, user_id)
        if user_data:
            user_data['last_activity_dt'] = datetime.now().timestamp()
            keyword = keyword.lower().strip()
            if len(user_data["keywords"]) < user_data['keywords_limit']:
                if keyword not in user_data['keywords']:
                    try:
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
                        session.commit()
                    except SQLAlchemyError as e:
                        self._db_error_handle(e)
                        return False    # DB error
                    user_data['keywords'].append(keyword)
                    self._keywords_update_required = True
            return True     # Success (even if the keyword was not added
                            # (already exist or the limit is exceeded))
        else:
            return False    # DB error


    async def remove_keyword(self, session: Session, user_id: int, keyword: str) -> bool:
        """
            Remove keyword from user's list in DB and in cached user data.
            Also set `_keywords_update_required` to True (need update keywords cache).
            Also update `last_activity_dt`.
            Returns `True` on success or `False` on DB error.
        """
        user_data = await self.get_user_data(session, user_id)
        if user_data:
            user_data['last_activity_dt'] = datetime.now().timestamp()
            try:
                subq = select(m.Keyword.id).where(m.Keyword.word == keyword)
                st = delete(m.user_keyword_link).where(m.user_keyword_link.c.user_id == user_id) \
                        .where(m.user_keyword_link.c.keyword_id.in_(subq))
                session.execute(st)
                session.commit()
            except SQLAlchemyError as e:
                self._db_error_handle(e)
                return False    # DB error
            if keyword in user_data['keywords']:
                user_data['keywords'].remove(keyword)
            self._keywords_update_required = True
            return True     # Success
        else:
            return False    # DB error


    def get_all_keywords(self, session: Session) -> Optional[dict]:
        """
            Return list of all keywords of users with enabled `forwarding`.
            If `_keywords_update_required` is True - request data from DB, 
            otherwise just return cached list.
            Returns:
                dict of keywords, where key is keyword and value is list of user ids
                `None` on DB error.
        """
        if self._keywords_update_required:
            self._keywords_cache = {}
            try:
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
            except SQLAlchemyError as e:
                self._db_error_handle(e)
                return False    # DB error
            self._update_required = False
        return self._keywords_cache     # Success
    
