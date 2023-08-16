import os

from pydantic import SecretStr
from pydantic_settings import BaseSettings

start_path = os.path.dirname(__file__)
dotenv_path = os.path.join(start_path, '.env')

class Settings(BaseSettings):
    TEST: int
    REDIS_DB: int
    BOT_TOKEN: SecretStr
    DB_DNS: str
    API_ID: int
    API_HASH: SecretStr
    PHONE: str

    class Config:
        env_file = dotenv_path
        env_file_encoding = 'utf-8'


config = Settings()
