import os

from pydantic import SecretStr, BaseSettings
#from pydantic_settings import BaseSettings

start_path = os.path.dirname(__file__)
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')

class Settings(BaseSettings):
    BOT_TOKEN: SecretStr
    DB_DNS: str
    API_ID: int
    API_HASH: SecretStr

    class Config:
        env_file = dotenv_path
        env_file_encoding = 'utf-8'


config = Settings()
