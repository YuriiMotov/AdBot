import  asyncio
from collections import deque
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
        self._queue: deque[asyncio.Task] = deque()


    def subscribe(self, events: Sequence[AdBotEvent], handler: EventHandler) -> None:
        """
            Add callback for event types, specified in `events` parameter
            (list of event types).
            Raises MessageBusException:
                If event type is not subclass of AdBotEvent.
                On duplicated handler.
        """
        event_types = set(map(lambda x: x.__name__, events))
        logger.debug(
            f'Messagebus. Subscribe {handler} for events ({", ".join(event_types)})'
        )
        for event in events:
            if not issubclass(event, AdBotEvent):
                e = MessageBusException(
                    f"Wrong event type: {event.__name__} is not a subclass of AdBotEvent"
                )
                logger.error(f'Messagebus. Exception: {e}')
                raise e
        if handler in self._subscribers.keys():
            logger.error(f"Messagebus. Duplicated handler: {handler}")
            raise MessageBusException(f"Duplicated handler: {handler}")
        self._subscribers[handler] = event_types


    def post_event(self, event: AdBotEvent) -> None:
        """
            Posts the event. Starts asyncio task to process this event by each subsrcibed
            handler.
        """
        logger.debug(f'Messagebus. Event posted: {event.__class__.__name__}')
        catched = False
        event_cls = event.__class__.__name__
        for handler, events_str in self._subscribers.items():
            if event_cls in events_str:
                logger.debug(
                    f'Messagebus. Event {event.__class__.__name__} handled by handler' \
                        ' {handler}'
                )
                catched = True
                self._queue.append(asyncio.create_task(handler(event)))
        if not catched:
            logger.warning(
                f'Messagebus. Handlers not found for event {event.__class__.__name__}'
            )
        
        # pop finished tasks from queue
        while self._queue and self._queue[0].done():
            self._queue.popleft()


    async def wait_for_tasks_done(self):
        logger.debug(f'Waiting for tasks in messagebus queue to be done')
        tasks = asyncio.gather(*self._queue, return_exceptions=True)
        
        try:
            await asyncio.wait_for(tasks, timeout=10)
        except (asyncio.TimeoutError, asyncio.exceptions.CancelledError):
            logger.error(f'Some tasks in messagebus queue were cancelled')
        else:
            logger.debug(f'All tasks in messagebus queue are done')
            return
        
        try:
            await tasks
        except asyncio.exceptions.CancelledError:
            pass
           

