from enum import Enum


class Lang(str, Enum):
    en: str = "en"
    ru: str = "ru"


class SourceType(str, Enum):
    telegram: str = "telegram"
    facebook: str = "facebook"

