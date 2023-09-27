from abc import ABC, abstractmethod

from adbot.domain import events
from adbot.domain.services import AdBotServices

class PresentationInterface(ABC):

    def __init__(self, ad_bot_srv: AdBotServices) -> None:
        self._ad_bot_srv = ad_bot_srv

    @abstractmethod
    async def run(self):
        raise NotImplementedError

    @abstractmethod
    async def stop_event_handler(self):
        raise NotImplementedError

    @abstractmethod
    async def user_inactivity_timeout_handler(self, event: events.AdBotInactivityTimeout):
        raise NotImplementedError
    
    @abstractmethod
    async def user_data_updated_handler(self, event: events.AdBotUserDataUpdated):
        raise NotImplementedError
    
    @abstractmethod
    async def user_message_forward_request_handler(
        self, event: events.AdBotMessageForwardRequest
    ):
        raise NotImplementedError
    