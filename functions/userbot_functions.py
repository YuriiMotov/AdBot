from hashlib import md5

from sqlalchemy.orm import Session

from db.models import GroupChatMessage
from .session_decorator import add_session


@add_session
async def add_groupchat_msg(session: Session, text: str, url: str) -> None:
    chat_msg = GroupChatMessage(
        text=text,
        url=url,
        text_hash=md5(text.encode('utf-8'), usedforsecurity=False).hexdigest(),
        processed=False
    )
    session.add(chat_msg)
    session.commit()
