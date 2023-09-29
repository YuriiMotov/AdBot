from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings

dotenv_path = '.env'


class Settings(BaseSettings):
    
    MODE: str = 'DEPLOY'
    ADMIN_ID: int

    # DB type
    DB_TYPE: Literal['PG', 'SQLITE'] = 'PG'

    # PostgreSQL DB
    PG_DB_DRV: str = 'psycopg'
    PG_DB_HOST: str = 'postgres'
    PG_DB_PORT: int = 5432
    PG_DB_USER: str = 'user'
    PG_DB_PWD: SecretStr = ''
    PG_DB_DBNAME: str = 'adbot_db'

    # # SQLite DB
    SQLITE_DB_DSN: str = 'sqlite+aiosqlite:///database.db'

    # Aiogram bot config
    REDIS_DB: int
    BOT_TOKEN: SecretStr

    # Telethon config    
    API_ID: int
    API_HASH: SecretStr
    PHONE: str

    # Testing config
    TESTBOT_NAME: str = ''
    CLIENT_ID: int = 0
    CHATS_FILTER: str = ''


    def get_db_dsn(self) -> str:
        if self.DB_TYPE == 'PG':
            return self._get_pg_dsn()
        elif self.DB_TYPE == 'SQLITE':
            return self.SQLITE_DB_DSN
        else:
            return ''


    def _get_pg_dsn(self) -> str:
        return (f'postgresql+{self.PG_DB_DRV}://{self.PG_DB_USER}:{self.PG_DB_PWD}'\
            f'@{self.PG_DB_HOST}:{self.PG_DB_PORT}/{self.PG_DB_DBNAME}')


    class Config:
        env_file = dotenv_path
        env_file_encoding = 'utf-8'


config = Settings()
