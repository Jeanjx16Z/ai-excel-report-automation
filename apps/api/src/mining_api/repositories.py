"""Hash-only in-memory session repository for a single local process."""

from dataclasses import dataclass
from datetime import datetime
from threading import RLock
from typing import Protocol
from uuid import UUID

from .errors import ApiError


@dataclass(frozen=True)
class SessionRecord:
    owner_id: UUID
    token_hash: str
    csrf_hash: str
    expires_at: datetime
    revoked: bool = False


class SessionRepository(Protocol):
    def get(self, token_hash: str) -> SessionRecord | None: ...
    def save(self, record: SessionRecord, now: datetime) -> None: ...
    def replace(self, old_hash: str, record: SessionRecord, now: datetime) -> None: ...
    def revoke(self, token_hash: str) -> None: ...


class InMemorySessionRepository:
    def __init__(self, capacity: int = 1000):
        self._records: dict[str, SessionRecord] = {}
        self._lock = RLock()
        self._capacity = capacity

    def get(self, token_hash: str) -> SessionRecord | None:
        with self._lock:
            return self._records.get(token_hash)

    def save(self, record: SessionRecord, now: datetime) -> None:
        with self._lock:
            self._records = {key: value for key, value in self._records.items()
                             if not value.revoked and value.expires_at > now}
            if len(self._records) >= self._capacity:
                raise ApiError("SERVICE_UNAVAILABLE")
            self._records[record.token_hash] = record

    def replace(self, old_hash: str, record: SessionRecord, now: datetime) -> None:
        with self._lock:
            old = self._records.get(old_hash)
            if not old or old.revoked or old.expires_at <= now:
                raise ApiError("INVALID_SESSION")
            self._records.pop(old_hash)
            self._records[record.token_hash] = record

    def revoke(self, token_hash: str) -> None:
        with self._lock:
            old = self._records.get(token_hash)
            if old:
                from dataclasses import replace
                self._records[token_hash] = replace(old, revoked=True)
