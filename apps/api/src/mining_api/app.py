"""Application factory with a controlled service boundary and safe diagnostics."""

import logging
import secrets
from typing import Callable
from uuid import UUID, uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException

from .config import Settings
from .errors import ApiError, error_response
from .repositories import InMemorySessionRepository, SessionRepository
from .routes import router
from .sessions import SessionService, utc_now
from .report_routes import router as report_router
from .report_service import ReportService
from .storage import LocalPrivateStorage

logger = logging.getLogger("mining_api")


def canonical_request_id(value: str | None) -> str:
    try:
        if value and len(value) == 36 and str(UUID(value)) == value.lower():
            return str(UUID(value))
    except ValueError:
        pass
    return str(uuid4())


def create_app(settings: Settings | None = None,
               repository: SessionRepository | None = None,
               clock: Callable = utc_now) -> FastAPI:
    settings = settings if settings is not None else Settings.from_environment()
    app = FastAPI(title="Synthetic Mining Reporting API", docs_url=None, redoc_url=None,
                  openapi_url=None, redirect_slashes=False)
    app.state.settings = settings
    app.state.sessions = SessionService(
        repository if repository is not None else InMemorySessionRepository(),
        settings.session_ttl_seconds, clock,
    )
    app.state.reports = ReportService(LocalPrivateStorage(settings.runtime_dir), clock, settings.report_ttl_seconds)

    @app.middleware("http")
    async def boundary(request: Request, call_next):
        request_id = canonical_request_id(request.headers.get("x-request-id"))
        request.state.request_id = request_id
        try:
            host = request.url.hostname
            supplied = request.headers.get("x-api-proxy-secret", "")
            if (host not in settings.allowed_hosts
                    or not secrets.compare_digest(supplied.encode(),
                                                  settings.proxy_secret.get_secret_value().encode())
                    or any(name.lower() == "forwarded" or name.lower().startswith("x-forwarded-")
                           for name in request.headers)):
                raise ApiError("UNTRUSTED_PROXY")
            origin = request.headers.get("origin")
            if origin is not None and origin != settings.frontend_origin:
                raise ApiError("UNTRUSTED_PROXY")
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                if origin != settings.frontend_origin:
                    raise ApiError("CSRF_REJECTED")
                if request.method == "POST" and request.headers.get("content-type", "").split(";")[0] != "application/json":
                    raise ApiError("INVALID_REQUEST")
            response = await call_next(request)
        except ApiError as error:
            response = error_response(error.code, request_id, error.report_id)
        except Exception:
            # Fixed fields only: no exception string, headers, query, path, cookie, or traceback.
            logger.error("internal_failure request_id=%s", request_id)
            response = error_response("PROCESSING_FAILURE", request_id)
        response.headers["X-Request-ID"] = request_id
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        logger.info("request_completed request_id=%s status=%d", request_id, response.status_code)
        return response

    @app.exception_handler(ApiError)
    async def domain_error(request: Request, error: ApiError):
        return error_response(error.code, request.state.request_id, error.report_id)

    @app.exception_handler(RequestValidationError)
    async def invalid_request(request: Request, error: RequestValidationError):
        return error_response("INVALID_REQUEST", request.state.request_id)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        code = {404: "NOT_FOUND", 405: "METHOD_NOT_ALLOWED"}.get(error.status_code, "INVALID_REQUEST")
        response = error_response(code, request.state.request_id)
        if error.status_code == 405 and error.headers and "Allow" in error.headers:
            response.headers["Allow"] = error.headers["Allow"]
        return response

    app.include_router(router)
    app.include_router(report_router)
    return app
