from sqlalchemy.orm import Session, sessionmaker
from collections.abc import Awaitable, Callable
from functools import wraps
from inspect import iscoroutinefunction
from typing import ParamSpec, TypeVar, cast, overload, Concatenate, Optional

_db_session_maker: Optional[sessionmaker] = None

def set_session_maker(db_sessionmaker: sessionmaker) -> None:
    global _db_session_maker
    _db_session_maker = db_sessionmaker


P = ParamSpec('P')
R = TypeVar('R')

def add_session(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    
    async def async_inner(*args: P.args, **kwargs: P.kwargs) -> R:
        with _db_session_maker() as session:
            result = await cast(Awaitable[R], func(session, *args, **kwargs))
        return result
    
    return wraps(func)(async_inner)



