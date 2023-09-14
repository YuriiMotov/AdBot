from aiogram.filters import Filter
from aiogram.types import Message


class SenderId(Filter):
    def __init__(self, sender_id: int) -> None:
        self._sender_id = sender_id

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id == self._sender_id
