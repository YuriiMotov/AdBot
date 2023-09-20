from pydantic import SecretStr
from pydantic_settings import BaseSettings

dotenv_path = '.env'

class Settings(BaseSettings):
    MODE: str = 'DEPLOY'
    ADMIN_ID: int
    TEST: int
    REDIS_DB: int
    BOT_TOKEN: SecretStr
    TESTBOT_NAME: str = ''
    CLIENT_ID: int = 0
    DB_DNS: str
    API_ID: int
    API_HASH: SecretStr
    CHATS_FILTER: str = ''
    PHONE: str

    class Config:
        env_file = dotenv_path
        env_file_encoding = 'utf-8'


config = Settings()
