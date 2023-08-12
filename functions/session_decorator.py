import logging
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar, cast, Concatenate, Optional

_db_session_maker: Optional[sessionmaker] = None

def set_session_maker(db_sessionmaker: sessionmaker) -> None:
    global _db_session_maker
    _db_session_maker = db_sessionmaker


P = ParamSpec('P')
R = TypeVar('R')

def add_session(func: Callable[Concatenate[Session, P], Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    
    async def async_inner(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            with _db_session_maker() as session:
                result = await cast(Awaitable[R], func(session, *args, **kwargs))
            return result
        except SQLAlchemyError as e:
            logging.error(e)
            return None


    return wraps(func)(async_inner)



