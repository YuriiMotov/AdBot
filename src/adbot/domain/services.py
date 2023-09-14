import asyncio
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta
from hashlib import md5
import logging
from typing import Optional, TypeAlias, Union

from sqlalchemy.orm import Session, sessionmaker, load_only, with_expression, selectinload
from sqlalchemy import select, func
from sqlalchemy.exc import SQLAlchemyError

from .messagebus import MessageBus
from . import events
from . import models
from . import exceptions as exc


# UserDict: TypeAlias = dict[str, Union[bool, str, int, float, list[int | str]]]
# ForwardFunc: TypeAlias = Callable[[int, str], Awaitable[bool]]

IDLE_TIMEOUT_MINUTES = 2
CHECK_IDLE_CYCLES = 10
CHECK_IDLE_INTERVAL_SEC = 20

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class AdBotServices():

    def __init__(self, db_pool: sessionmaker):
        """
            Initializes object, preload data from DB into cache (menu_closed states).
            Raises `AdBotExceptionSQL` exception on DB error.
        """
        self._stop = True
        self._stopped = True
        self._db_pool = db_pool
        self.messagebus = MessageBus()
        self._updated_uids = set()  # ids of users whose data were updated by _process_messages method

        # Set last_activity_dt for all users with menu_closed=False
        self._menu_activity_cache = {}  #cached data (menu_closed and laste_activity_dt)
        st = select(models.User.id).where(models.User.menu_closed == False)
        try:
            with self._db_pool() as session:
                for user_id in session.scalars(st).all():
                    self._menu_activity_cache[user_id] = {
                        'menu_closed': False,
                        'act_dt': datetime.now()
                    }
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    def _db_error_handle(self, error: SQLAlchemyError) -> None:
        logger.error(f'Exception {error.__class__} {error}')


    def _get_user_by_id(self, session: Session, user_id: int) -> models.User:
        """
            Returns `user` object by primary key `id`.
            Gets `session` as a parameter.
            Raises:
                `AdBotExceptionUserNotExist` if user doesn't exist
                `AdBotExceptionSQL` exception on DB error
        """
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
            user = session.scalar(st)
            if user is not None:
                return user
            raise exc.AdBotExceptionUserNotExist(f"User with id={user_id} doesn`t exist")
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    async def get_user_by_id(self, user_id: int) -> models.User:
        """
            Returns `user` object by primary key `id`.
            Raises:
                `AdBotExceptionUserNotExist` if user doesn't exist
                `AdBotExceptionSQL` exception on DB error
        """
        try:
            with self._db_pool() as session:
                return self._get_user_by_id(session, user_id)
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")
        

    async def get_user_by_telegram_id(self, telegram_id: int) -> models.User:
        """
            Returns `user` object by `telegram_id` key.
            Raises:
                `AdBotExceptionUserNotExist` if user doesn't exist
                `AdBotExceptionSQL` exception on DB error
        """
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
                user = session.scalar(st)
                if user is not None:
                    return user
                raise exc.AdBotExceptionUserNotExist(
                    f"User with telegram_id={telegram_id} doesn`t exist"
                )
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    async def create_user_by_telegram_data(self, telegram_id: int, telegram_name: str) -> models.User:
        """
            Creates user.
            Returns created user's `user` object.
            Raises `AdBotExceptionSQL` exception on DB error.
        """
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
        
        try:
            return await self.get_user_by_telegram_id(telegram_id)
        except exc.AdBotExceptionUserNotExist:
            raise exc.AdBotExceptionSQL("SQLAlchemyError")

    async def get_or_create_user_by_telegram_data(
            self, telegram_id: int, telegram_name: str
    ) -> models.User:
        """
            Returns `user` object by `telegram_id` key.
            Creates user if doesn't exist.
            Raises:
                `AdBotExceptionSQL` exception on DB error
        """
        try:
            return await self.get_user_by_telegram_id(telegram_id)
        except exc.AdBotExceptionUserNotExist:
            return await self.create_user_by_telegram_data(telegram_id, telegram_name)



    # Subscription management

    async def set_subscription_state(self, user_id: int, new_state: bool) -> None:
        """
            Sets subscription state to `new_state`.
            Subscription state determines whether messages will be filtered for this user
            (messages will be added to forward_queue of this user).
            Raises:
                `AdBotExceptionUserNotExist` if user doesn`t exist
                `AdBotExceptionSQL` exception on DB error
        """
        try:
            with self._db_pool() as session:
                user = self._get_user_by_id(session, user_id)
                user.subscription_state = new_state
                session.commit()
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    # Forwarding state management

    async def set_forwarding_state(self, user_id: int, new_state: bool) -> bool:
        """
            Sets forwarding state to `new_state`.
            Forwarding state determines whether messages will be sended to this user
            (AdBotMessageForwardRequest events will be generated).
            Raises:
                `AdBotExceptionUserNotExist` if user doesn`t exist
                `AdBotExceptionSQL` exception on DB error
        """
        try:
            with self._db_pool() as session:
                user = self._get_user_by_id(session, user_id)
                user.forwarding_state = new_state
                session.commit()
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    # Menu closed state management

    async def set_menu_closed_state(self, user_id: int, new_state: bool) -> bool:
        """
            Sets menu_closed state to `new_state`.
            Menu_closed=False means that user opened the menu.
            When the menu is open, messages will not be forwarded to this user untill the menu is closed.
            Raises:
                `AdBotExceptionUserNotExist` if user doesn`t exist
                `AdBotExceptionSQL` exception on DB error
        """
        try:
            with self._db_pool() as session:
                user = self._get_user_by_id(session, user_id)
                user.menu_closed = new_state
                session.commit()
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")
        # update data in _menu_activity_cache
        if new_state:
            self._menu_activity_cache.pop(user_id, None)
        else:
            self._menu_activity_cache[user_id] = {
                'menu_closed': False,
                'act_dt': datetime.now()
            }


    # Idle timeout managment

    async def reset_inactivity_timer(self, user_id) -> None:
        """
            Updates `last activity dt` in cache, sets it to now().
            `last activity dt` is used to determine when user forgot to close the menu.
            After some time (IDLE_TIMEOUT_MINUTES) system will send command to close the menu.
        """
        user_menu_activity_data = self._menu_activity_cache.get(user_id)
        if user_menu_activity_data is None:
            logger.error(f'reset_inactivity_timer called for user with closed menu: {user_id}')
            user_menu_activity_data = {'menu_closed': False}
            self._menu_activity_cache[user_id] = user_menu_activity_data
        user_menu_activity_data['act_dt'] = datetime.now()

   
    async def get_is_idle_with_opened_menu(self, user_id: int) -> bool:
        """
            Returns True if user menu is open, but user is not active for some time (IDLE_TIMEOUT_MINUTES).
            Uses cached data to determine whether the menu is open and idle timeout is riched.
        """
        time_point = datetime.now() - timedelta(minutes=IDLE_TIMEOUT_MINUTES)

        umad = self._menu_activity_cache.get(user_id)
        if umad:
            return (umad['menu_closed'] == False) and (umad['act_dt'] < time_point)
        return False


    # Keywords management

    async def add_keyword(self, user_id: int, keyword: str) -> bool:
        """
            Adds keyword to user's list.
            If keyword exist in DB, then just add link between keyword and user.
            If keyword is already in user's list, then do nothing.
            Returns True on success.
            Raises:
                `AdBotExceptionUserNotExist` if user doesn`t exist
                `AdBotExceptionSQL` exception on DB error
        """
        try:
            with self._db_pool() as session:
                user = self._get_user_by_id(session, user_id)
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


    async def remove_keyword(self, user_id: int, keyword: str) -> bool:
        """
            Removes keyword from user's list.
            If keyword is not in user's list, then do nothing.
            Returns True on success.
            Raises:
                `AdBotExceptionUserNotExist` if user doesn`t exist
                `AdBotExceptionSQL` exception on DB error
        """
        try:
            with self._db_pool() as session:
                user = self._get_user_by_id(session, user_id)
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

    async def add_message(self, cat_id: int, source_id: int, msg_text: str, url: str) -> bool:
        """
            Inserts message into DB.
            Returns True on success.
            Raises:
                `AdBotExceptionSQL` exception on DB error
        """
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


    async def _process_messages(self) -> None:
        """
            Filters unprocessed messages, puts them to users's forward queues according to
            total keywords list (only for users with `subscription state` = True)
            Raises:
                `AdBotExceptionSQL` exception on DB error  
        """
        try:
            with self._db_pool() as session:
                keywords = await self._get_all_keywords(session)
                st = select(models.GroupChatMessage).where(models.GroupChatMessage.processed == False)
                msgs = session.scalars(st).all()
                for msg in msgs:
                    msg_text = msg.text.lower()
                    for kw, user_ids in keywords.items():
                        if kw in msg_text:
                            for user_id in user_ids:
                                user = session.get(models.User, user_id)
                                user.forward_queue.append(msg)
                                self._updated_uids.add(user.id)
                    msg.processed = True
                session.commit()
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    async def _get_all_keywords(self, session: Session) -> Optional[dict]:
        """
            Creates total list of all keywords of users with `subscription state`=True.
            Returns dict of keywords, where key is keyword and value is list of users ids.
            Raises:
                SQLAlchemyError on DB error
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


    async def _forward_messages(self) -> None:
        """
            Generates `AdBotMessageForwardRequest` events for every message in user's forward queue.
            Removes messages from user's forward queues.
            Only for users with `forwarding` = True.
            Raises:
                SQLAlchemyError on DB error
        """
        try:
            with self._db_pool() as session:
                st = select(models.User) \
                    .where(models.User.forwarding_state == True) \
                    .options(selectinload(models.User.forward_queue))
                users = session.scalars(st).all()
                for user in users:
                    for msg in list(user.forward_queue):
                        if user.menu_closed == True:
                            event = events.AdBotMessageForwardRequest(
                                user_id=user.id,
                                telegram_id=user.telegram_id,
                                message_url=msg.url,
                                message_text=msg.text
                            )
                            self.messagebus.post_event(event)
                            user.forward_queue.remove(msg)
                session.commit()
        except SQLAlchemyError as e:
            self._db_error_handle(e)
            raise exc.AdBotExceptionSQL("SQLAlchemyError")


    async def _check_idle_timeouts(self) -> None:
        """
            Generates `AdBotInactivityTimeout` events for inactive users with opened menu.
            Uses cached data to determine whether the menu is open and idle timeout is riched.
        """
        for uid in self._menu_activity_cache.keys():
            if await self.get_is_idle_with_opened_menu(uid):
                self.messagebus.post_event(events.AdBotInactivityTimeout(uid))
        

    async def _check_user_data_updated(self) -> None:
        """
            Generates `AdBotUserDataUpdated` events for users with opened menu whose data was updated by `_process_messages`
            (messages to `forward_queue` were added).
            Uses cached data to determine whether the menu is open and data were updated.
        """
        updated_uids = self._updated_uids
        self._updated_uids = set()
        for uid in updated_uids:
            if uid in self._menu_activity_cache:
                umad = self._menu_activity_cache[uid]
                if umad['menu_closed'] == False:
                    self.messagebus.post_event(events.AdBotUserDataUpdated(uid))


    async def run(self) -> None:
        """
            Runs Main cycle.
            Reraises any exceptions except `AdBotExceptionSQL`.
            Posts `AdBotStop` event after loop exit.
        """
        logger.debug(f"Start main cycle at {datetime.now()}")
        self._stop = False
        self._stopped = False
        try:
            await self._loop()
        finally:
            self._stop = True
            self._stopped = True
            self.messagebus.post_event(events.AdBotStop())


    async def _loop(self) -> None:
        """
            Processes messages (filter by users's keywords).
            Generates `AdBotMessageForwardRequest` events to forward messages to users.
            Checks users's inactivity state and generates `AdBotInactivityTimeout` to close menus of inactive users.
            Generates `AdBotUserDataUpdated` events for users with opened menu whose data was updated.
        """
        while not self._stop:
            counter = CHECK_IDLE_CYCLES
            while (not self._stop) and (counter > 0):
                logger.debug(f"Check idle timeouts")
                await self._check_idle_timeouts()
                await asyncio.sleep(CHECK_IDLE_INTERVAL_SEC)
                counter -= 1

            if  not self._stop:
                logger.debug(f"Process messages")
                try:
                    await self._process_messages()
                except exc.AdBotExceptionSQL:
                    logger.error(f'Database error during processing messages')

                logger.debug(f"Forward messages")
                try:
                    await self._forward_messages()
                except exc.AdBotExceptionSQL:
                    logger.error(f'Database error during forwarding messages')
                
                logger.debug(f"Forward messages")
                await self._check_user_data_updated()


    async def stop(self) -> None:
        """
            Stops main cycle.
            Sets `stop` flag to True and wait untill main cycle stopped.
            `AppStop` event will be posted after loop exit.
        """
        logger.debug(f"Stopping main cycle at {datetime.now()}")
        self._stop = True
        while not self._stopped:
            await asyncio.sleep(0.5)
        logger.debug(f"Main cycle stopped at {datetime.now()}")



