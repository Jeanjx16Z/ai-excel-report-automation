"""Session service and ownership context independent of transport routes."""

from datetime import datetime, timedelta, timezone
from hashlib import sha256
import re
import secrets
from typing import Callable
from uuid import UUID, uuid4

from .errors import ApiError
from .repositories import SessionRecord, SessionRepository

COOKIE_NAME = "mining_session"
TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_-]{43}\Z")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def digest(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


class SessionService:
    def __init__(self, repository: SessionRepository, ttl: int,
                 clock: Callable[[], datetime] = utc_now):
        self.repository = repository
        self.ttl = ttl
        self.clock = clock

    def resolve(self, token: str | None) -> SessionRecord:
        if not token or not TOKEN_PATTERN.fullmatch(token):
            raise ApiError("INVALID_SESSION")
        record = self.repository.get(digest(token))
        if not record or record.revoked or record.expires_at <= self.clock():
            raise ApiError("INVALID_SESSION")
        return record

    def verify_csrf(self, record: SessionRecord, csrf: str | None) -> None:
        if not csrf or not TOKEN_PATTERN.fullmatch(csrf) or not secrets.compare_digest(
            record.csrf_hash, digest(csrf)
        ):
            raise ApiError("CSRF_REJECTED")

    def issue(self, old: SessionRecord | None = None):
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        now = self.clock()
        # Rotation preserves ownership but never extends the original absolute lifetime.
        record = SessionRecord(
            owner_id=old.owner_id if old else uuid4(), token_hash=digest(token),
            csrf_hash=digest(csrf),
            expires_at=old.expires_at if old else now + timedelta(seconds=self.ttl),
        )
        if old:
            self.repository.replace(old.token_hash, record, now)
        else:
            self.repository.save(record, now)
        return record, token, csrf


def require_same_owner(identity: SessionRecord, resource_owner_id: UUID) -> None:
    """Use server-owned metadata, never a client-provided owner identifier."""
    if identity.owner_id != resource_owner_id:
        raise ApiError("NOT_FOUND")
