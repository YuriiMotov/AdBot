from abc import ABC, abstractmethod
from collections.abc import Callable, Awaitable
from typing import TypeAlias

AddMessageHandler: TypeAlias = Callable[[int, int, str, str], Awaitable[bool]]

class MessageFetcher(ABC):
    def __init__(self, add_message_handler: AddMessageHandler):
        self._add_message_handler = add_message_handler
    
    @abstractmethod
    async def fetch_messages(self) -> None:
        raise NotImplementedError
