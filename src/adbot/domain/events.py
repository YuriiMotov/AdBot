from dataclasses import dataclass


class AdBotEvent:
    pass


@dataclass
class AdBotUserDataUpdated(AdBotEvent):
    user_id: int


@dataclass
class AdBotInactivityTimeout(AdBotEvent):
    user_id: int


@dataclass
class AdBotCriticalError(AdBotEvent):
    error_msg: str


@dataclass
class AdBotMessageForwardRequest(AdBotEvent):
    user_id: int
    telegram_id: int
    message_url: str
    message_text: str

@dataclass
class AdBotStop(AdBotEvent):
    pass
