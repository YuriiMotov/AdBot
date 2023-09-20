from aiogram.filters import Filter
from aiogram.types import Message


class ChatId(Filter):
    def __init__(self, chat_id: int) -> None:
        self._chat_id = chat_id

    async def __call__(self, message: Message) -> bool:
        return message.chat.id == self._chat_id


class ChatName(Filter):
    def __init__(self, chat_name: int) -> None:
        self._chat_name = chat_name

    async def __call__(self, message: Message) -> bool:
        return message.chat.full_name == self._chat_name


class SenderId(Filter):
    def __init__(self, sender_id: int) -> None:
        self._sender_id = sender_id

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id == self._sender_id
