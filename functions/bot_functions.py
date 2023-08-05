from datetime import datetime
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.types import Chat, User, Message, Update
from sqlalchemy.orm import Session

from .data_cached import DataCached, UserDict
from .session_decorator import add_session

data: DataCached = DataCached()

bot: Bot = None
dp: Dispatcher = None


@add_session
async def get_user(session: Session, user_id: int) -> Optional[UserDict]:
    return await data.get_user_data(session, user_id)


@add_session
async def add_user(session: Session, user_id: int, user_name: str) -> Optional[UserDict]:
    return await data.add_user(session, user_id, user_name)


@add_session
async def add_keyword(session: Session, user_id: int, keyword: str) -> UserDict:
    return await data.add_keyword(session, user_id, keyword)


@add_session
async def remove_keyword(session: Session, user_id: int, keyword: str) -> UserDict:
    return await data.remove_keyword(session, user_id, keyword)


@add_session
async def set_forwarding_state(session: Session, user_id: int, new_state: bool) -> UserDict:
    return await data.set_forwarding_state(session, user_id, new_state)


@add_session
async def set_menu_closed_state(session: Session, user_id: int, closed: bool) -> None:
    return await data.set_menu_closed_state(session, user_id, closed)


@add_session
async def get_menu_closed_state(session: Session, user_id: int) -> None:
    return await data.get_menu_closed_state(session, user_id)


@add_session
async def reset_inactivity_timer(session: Session, user_id: int) -> None:
    return await data.reset_inactivity_timer(session, user_id)


@add_session
async def refresh_user_data(session: Session, user_id: int) -> None:
    return await data.refresh_user_data(session, user_id)



# Scheduler tasks

@add_session
async def forward_messages(session: Session) -> None:
    async def forward_msg(user_id: int, msg_text: str) -> bool:
        await bot.send_message(
            chat_id=user_id,
            text=msg_text,
            disable_notification=True
        )
        return True

    await data.forward_msgs(session, forward_msg)


@add_session
async def process_groupchat_messages(session: Session):
    await data.process_groupchat_messages(session)


@add_session
async def check_opened_dialogs(session: Session) -> None:
    # Close dialogs of incative users
    user_ids = await data.get_inactive_users(session)
    for user_id in user_ids:
        await _bot_send_command(user_id, '/close_dialog')

    # Refrech dialogs for active users
    user_ids = await data.get_active_users(session)
    for user_id in user_ids:
        await data.refresh_user_data(session, user_id)          # Refresh data in the cache
        await _bot_send_command(user_id, '/refresh_dialog')     # Send cmd to refresh window


async def _bot_send_command(user_id: int, command: str) -> None:
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