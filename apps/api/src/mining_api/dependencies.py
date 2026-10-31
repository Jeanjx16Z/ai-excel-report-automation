"""Request-scoped service and identity dependencies."""

from fastapi import Request

from .repositories import SessionRecord
from .sessions import COOKIE_NAME, SessionService


def get_session_service(request: Request) -> SessionService:
    return request.app.state.sessions


def get_identity(request: Request) -> SessionRecord:
    return get_session_service(request).resolve(request.cookies.get(COOKIE_NAME))
