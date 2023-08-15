from hashlib import md5
import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from db.models import GroupChatMessage
from .session_decorator import add_session

logger = logging.getLogger(__name__)


@add_session
async def add_groupchat_msg(session: Session, text: str, url: str) -> bool:
    logger.debug(f'add_groupchat_msg {url}')
    chat_msg = GroupChatMessage(
        text=text,
        url=url,
        text_hash=md5(text.encode('utf-8'), usedforsecurity=False).hexdigest(),
        processed=False
    )
    try:
        session.add(chat_msg)
        session.commit()
        return True
    except SQLAlchemyError as e:
        logger.debug(f'add_groupchat_msg Exception {e.__class__} {e}')
        return False
