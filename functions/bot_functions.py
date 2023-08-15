from datetime import datetime
import logging
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.types import Chat, User, Message, Update
from sqlalchemy.orm import Session

from .data_cached import DataCached, UserDict
from .session_decorator import add_session

data: DataCached = DataCached()

bot: Bot = None
dp: Dispatcher = None

logger = logging.getLogger(__name__)

@add_session
async def get_user(session: Session, user_id: int) -> Optional[UserDict]:
    logger.debug(f'get_user {user_id}')
    return await data.get_user_data(session, user_id)


@add_session
async def add_user(session: Session, user_id: int, user_name: str) -> Optional[UserDict]:
    logger.debug(f'add_user {user_id}')
    return await data.add_user(session, user_id, user_name)


@add_session
async def get_user_add_refresh_reset(session: Session, user_id: int, user_name: str) -> Optional[UserDict]:
    logger.debug(f'get_user_add_refresh_reset {user_id}')
    user = await data.get_user_data(session, user_id)
    if user is None:
        logger.debug(f'get_user_add_refresh_reset {user_id}, user doesn`t exist. Add user')
        return await data.add_user(session, user_id, user_name)
    if await data.refresh_user_data(session, user_id) == False:
        logger.warning(f'get_user_add_refresh_reset {user_id}, refresh_user_data returned False')
    if await data.reset_inactivity_timer(session, user_id) == False:
        logger.warning(f'get_user_add_refresh_reset {user_id}, reset_inactivity_timer returned False')
    return user


@add_session
async def add_keyword(session: Session, user_id: int, keyword: str) -> Optional[bool]:
    logger.debug(f'add_keyword {user_id}, {keyword}')
    return await data.add_keyword(session, user_id, keyword)


@add_session
async def remove_keyword(session: Session, user_id: int, keyword: str) -> Optional[bool]:
    logger.debug(f'remove_keyword {user_id}, {keyword}')
    return await data.remove_keyword(session, user_id, keyword)


@add_session
async def set_forwarding_state(session: Session, user_id: int, new_state: bool) -> Optional[bool]:
    logger.debug(f'set_forwarding_state {user_id}, {new_state}')
    return await data.set_forwarding_state(session, user_id, new_state)


@add_session
async def set_menu_closed_state(session: Session, user_id: int, new_state: bool) -> Optional[bool]:
    logger.debug(f'set_menu_closed_state {user_id}, {new_state}')
    return await data.set_menu_closed_state(session, user_id, new_state)


@add_session
async def get_menu_closed_state(session: Session, user_id: int) -> Optional[bool]:
    logger.debug(f'get_menu_closed_state {user_id}')
    return await data.get_menu_closed_state(session, user_id)


@add_session
async def reset_inactivity_timer(session: Session, user_id: int) -> Optional[bool]:
    logger.debug(f'reset_inactivity_timer {user_id}')
    return await data.reset_inactivity_timer(session, user_id)


@add_session
async def refresh_user_data(session: Session, user_id: int) -> Optional[bool]:
    logger.debug(f'refresh_user_data {user_id}')
    return await data.refresh_user_data(session, user_id)


# Scheduler tasks

@add_session
async def forward_messages(session: Session) -> Optional[bool]:
    logger.debug(f'forward_messages')
    async def forward_msg(user_id: int, msg_text: str) -> bool:
        # ToDo: add error handling (try..except)?
        logger.debug(f'forward_msg {user_id}, "{msg_text[:20]}..."')
        return await bot.send_message(
            chat_id=user_id,
            text=msg_text,
            disable_notification=True
        )

    return await data.forward_msgs(session, forward_msg)


@add_session
async def process_groupchat_messages(session: Session) -> Optional[bool]:
    logger.debug(f'process_groupchat_messages')
    return await data.process_groupchat_messages(session)


@add_session
async def check_opened_dialogs(session: Session) -> Optional[bool]:
    logger.debug(f'check_opened_dialogs')
    # Close dialogs of incative users
    user_ids = await data.get_inactive_users(session)
    if user_ids:
        for user_id in user_ids:
            await _bot_send_command(user_id, '/close_dialog')
    else:
        pass
        # Log warning
    # Refrech dialogs for active users
    user_ids = await data.refresh_users_data(session)
    for user_id in user_ids:
        await _bot_send_command(user_id, '/refresh_dialog')     # Send cmd to refresh window
    return True


async def _bot_send_command(user_id: int, command: str) -> Optional[bool]:
    logger.debug(f'_bot_send_command {user_id}, {command}')
    user = User(id=user_id, is_bot=False, first_name='')
    chat = Chat(id=user_id, type='private')
    message = Message(
        message_id=0,
        date=datetime.now(),
        chat=chat,
        from_user=user,
        text=command
    )
    update = Update(update_id=0, message=message)
    await dp.propagate_event(
        update_type="update",
        event=update,
        bot=bot,
        event_from_user=user,
        event_chat=chat,
        **dp.workflow_data
    )
    return True