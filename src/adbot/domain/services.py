from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from hashlib import md5
import logging
from typing import Any, Optional, TypeAlias, Union

from sqlalchemy.orm import Session, sessionmaker, load_only, with_expression, selectinload
from sqlalchemy import select, delete, func
from sqlalchemy.exc import SQLAlchemyError

from adbot.domain import models
from . import exceptions as exc


UserDict: TypeAlias = dict[str, Union[bool, str, int, float, list[int | str]]]
ForwardFunc: TypeAlias = Callable[[int, str], Awaitable[bool]]

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AdBotServices():

    def __init__(self, db_pool: sessionmaker):
        self._db_pool = db_pool
        # TODO: preload data?

    def _db_error_handle(self, error: SQLAlchemyError) -> None:
        logger.error(f'Exception {error.__class__} {error}')


    def _get_user_by_id(self, session: Session, user_id: int) -> models.User:
        st = select(models.User) \
                .outerjoin_from(models.User, models.user_message_link).group_by(models.User.id) \
                .where(models.User.id == user_id) \
                .options(
                    selectinload(models.User.keywords),
                    with_expression(
                        models.User.forward_queue_len,
                        func.count(models.user_message_link.c.user_id)
                    )
                )
        try:
            return session.scalar(st)
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    def get_user_by_id(self, user_id: int) -> models.User:
        try:
            with self._db_pool() as session:
                return self._get_user_by_id(session, user_id)
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")
        

    def get_user_by_telegram_id(self, telegram_id: int) -> Optional[models.User]:
        try:
            with self._db_pool() as session:
                st = select(models.User) \
                        .outerjoin_from(models.User, models.user_message_link).group_by(models.User.id) \
                        .where(models.User.telegram_id == telegram_id) \
                        .options(
                            selectinload(models.User.keywords),
                            with_expression(
                                models.User.forward_queue_len,
                                func.count(models.user_message_link.c.user_id)
                            )
                        )
                return session.scalar(st)
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    def create_user_by_telegram_data(self, telegram_id: int, telegram_name: str) -> models.User:
        try:
            with self._db_pool() as session:
                user = models.User()
                user.telegram_id = telegram_id
                user.telegram_name = telegram_name
                user.forward_queue_len = 0
                session.add(user)
                session.commit()
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")
        
        user = self.get_user_by_telegram_id(telegram_id)
        if user:
            return user
        else:
            raise exc.AdBotExceptionSQL("SQLAlchemyError")



    # Subscription management

    def set_subscription_state(self, user_id: int, new_state: bool) -> bool:
        try:
            with self._db_pool() as session:
                user = self._get_user_by_id(session, user_id)
                if user is None:
                    raise exc.AdBotExceptionUserNotExist(f"User {user_id} doesn`t exist")
                user.subscription_state = new_state
                session.commit()
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    # Menu closed state management

    def set_menu_closed_state(self, user_id: int, new_state: bool) -> bool:
        try:
            with self._db_pool() as session:
                user = self._get_user_by_id(session, user_id)
                if user is None:
                    raise exc.AdBotExceptionUserNotExist(f"User {user_id} doesn`t exist")
                user.menu_closed = new_state
                session.commit()
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")



    # Keywords management

    def add_keyword(self, user_id: int, keyword: str) -> bool:
        try:
            with self._db_pool() as session:
                user = self._get_user_by_id(session, user_id)
                if user is None:
                    raise exc.AdBotExceptionUserNotExist(f"User {user_id} doesn`t exist")
                
                kw = session.scalar(select(models.Keyword).where(models.Keyword.word == keyword))
                if kw is None:
                    kw = models.Keyword(word=keyword)

                if kw not in user.keywords:
                    user.keywords.append(kw)
                session.commit()
            return True
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    def remove_keyword(self, user_id: int, keyword: str) -> bool:
        try:
            with self._db_pool() as session:
                user = self._get_user_by_id(session, user_id)
                if user is None:
                    raise exc.AdBotExceptionUserNotExist(f"User {user_id} doesn`t exist")
                kw = session.scalar(select(models.Keyword).where(models.Keyword.word == keyword))
                if kw:
                    if kw in user.keywords:
                        user.keywords.remove(kw)
                    session.commit()
            return True
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")
    

    # Messages management

    def add_message(self, cat_id: int, source_id: int, msg_text: str, url: str) -> bool:
        try:
            with self._db_pool() as session:
                msg = models.GroupChatMessage(
                    source_id=source_id,
                    cat_id=cat_id,
                    text=msg_text,
                    url=url,
                    text_hash=md5(msg_text.encode('utf-8'), usedforsecurity=False).hexdigest()
                )
                session.add(msg)
                session.commit()
            return True
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    def process_messages(self) -> None:
        try:
            with self._db_pool() as session:
                keywords = self._get_all_keywords(session)
                st = select(models.GroupChatMessage).where(models.GroupChatMessage.processed == False)
                msgs = session.scalars(st).all()
                for msg in msgs:
                    msg_text = msg.text.lower()
                    for kw, user_ids in keywords.items():
                        if kw in msg_text:
                            for user_id in user_ids:
                                user = session.get(models.User, user_id)
                                user.forward_queue.append(msg)
                    msg.processed = True
                session.commit()
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    def _get_all_keywords(self, session: Session) -> Optional[dict]:
        """
            Return list of all keywords of users with enabled `forwarding`.
            If `_keywords_update_required` is True - request data from DB, 
            otherwise just return cached list.
            Returns:
                dict of keywords, where key is keyword and value is list of user ids.
                Raises SQLAlchemyError on DB error.
        """
        if True: #self._keywords_update_required:
            self._keywords_cache = {}
            st = select(models.Keyword) \
                    .join_from(models.Keyword, models.user_keyword_link) \
                    .join_from(models.user_keyword_link, models.User) \
                    .where(models.User.subscription_state == True) \
                    .group_by(models.Keyword.id) \
                    .options(
                        selectinload(models.Keyword.users).options(load_only(models.User.id))
                    )
            
            for kw in session.scalars(st).all():
                self._keywords_cache[kw.word] = [user.id for user in kw.users if user.subscription_state]

        return self._keywords_cache     # Success

