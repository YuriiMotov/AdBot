import  asyncio
from collections.abc import Awaitable, Callable
import logging
from typing import Sequence, TypeAlias

from .events import AdBotEvent

logger = logging.getLogger(__name__)

EventHandler: TypeAlias = Callable[[AdBotEvent], Awaitable[None]]


class MessageBusException(Exception):
    pass


class MessageBus:

    def __init__(self):
        self._subscribers: dict[EventHandler, set[str]] = {}


    def subscribe(self, events: Sequence[AdBotEvent], handler: EventHandler) -> None:
        if handler in self._subscribers.keys():
            logger.warning(f"Duplicated handler: {handler}")
            raise MessageBusException(f"Duplicated handler: {handler}")
        self._subscribers[handler] = set(map(lambda c: c.__name__, events))


    def post_event(self, event: AdBotEvent) -> None:
        event_cls = event.__class__.__name__
        for handler, events_str in self._subscribers.items():
            if event_cls in events_str:
                asyncio.create_task(handler(event))

