import logging

from fastapi import FastAPI
from fastapi.exception_handlers import (
    http_exception_handler,
    request_validation_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from adbot.api.users.router import users_router
from adbot.api.keywords.router import keywords_router

logger = logging.getLogger(__name__)

app = FastAPI(
    title="AD Bot API server"
)

app.include_router(users_router)
app.include_router(keywords_router)

@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request, exc: StarletteHTTPException):
    logger.debug(f"{exc.__class__.__name__}: {repr(exc.detail)}")
    return await http_exception_handler(request, exc)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc: RequestValidationError):
    logger.debug(f"Request validation error: {exc}")
    return await request_validation_exception_handler(request, exc)






