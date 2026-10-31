"""Versioned transport routes: health and session lifecycle only."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, ConfigDict

from .dependencies import get_identity, get_session_service
from .errors import ErrorEnvelope
from .repositories import SessionRecord
from .sessions import COOKIE_NAME, SessionService

router = APIRouter(prefix="/api/v1", responses={
    status: {"model": ErrorEnvelope} for status in (401, 403, 404, 405, 422, 500, 503)
})


class EmptyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reset_ack: Literal[True]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"


class SessionResponse(BaseModel):
    active: bool = True
    expires_at: datetime


class IssuedSessionResponse(SessionResponse):
    csrf_token: str


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse()


def issue_cookie(request: Request, response: Response, service: SessionService,
                 old: SessionRecord | None = None):
    record, token, csrf = service.issue(old)
    response.set_cookie(
        COOKIE_NAME, token, httponly=True,
        secure=request.app.state.settings.cookie_secure, samesite="lax", path="/api/v1",
        max_age=max(0, int((record.expires_at - service.clock()).total_seconds())),
    )
    response.headers["Cache-Control"] = "no-store"
    return IssuedSessionResponse(expires_at=record.expires_at, csrf_token=csrf)


@router.post("/session", status_code=201, response_model=IssuedSessionResponse)
def bootstrap(body: EmptyRequest, request: Request, response: Response,
              service: Annotated[SessionService, Depends(get_session_service)]):
    # Existing cookies must go through authenticated rotation; unknown cookies are never adopted.
    if COOKIE_NAME in request.cookies:
        old = service.resolve(request.cookies[COOKIE_NAME])
        service.verify_csrf(old, request.headers.get("x-csrf-token"))
        return issue_cookie(request, response, service, old)
    return issue_cookie(request, response, service)


@router.get("/session", response_model=SessionResponse)
def current(identity: Annotated[SessionRecord, Depends(get_identity)]):
    return SessionResponse(expires_at=identity.expires_at)


@router.post("/session/reset", status_code=201, response_model=IssuedSessionResponse)
def reset(body: ResetRequest, request: Request, response: Response,
          service: Annotated[SessionService, Depends(get_session_service)]):
    # An explicit bootstrap reset creates a NEW owner, never grants the old owner's access.
    from .errors import ApiError
    try:
        old = service.resolve(request.cookies.get(COOKIE_NAME))
        service.repository.revoke(old.token_hash)
    except ApiError:
        pass
    return issue_cookie(request, response, service)


@router.post("/session/rotate", response_model=IssuedSessionResponse)
def rotate(body: EmptyRequest, request: Request, response: Response,
           identity: Annotated[SessionRecord, Depends(get_identity)],
           service: Annotated[SessionService, Depends(get_session_service)]):
    service.verify_csrf(identity, request.headers.get("x-csrf-token"))
    return issue_cookie(request, response, service, identity)


@router.delete("/session", status_code=204)
def revoke(request: Request,
           identity: Annotated[SessionRecord, Depends(get_identity)],
           service: Annotated[SessionService, Depends(get_session_service)]):
    service.verify_csrf(identity, request.headers.get("x-csrf-token"))
    service.repository.revoke(identity.token_hash)
    response = Response(status_code=204)
    response.delete_cookie(COOKIE_NAME, path="/api/v1", httponly=True,
                           secure=request.app.state.settings.cookie_secure, samesite="lax")
    return response
