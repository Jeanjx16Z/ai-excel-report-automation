"""Private local object adapter. Only server-generated opaque keys are accepted."""

from pathlib import Path
import re
import shutil
import time
from typing import Protocol
from uuid import uuid4


class ObjectStorage(Protocol):
    def allocate(self, suffix: str = "") -> str: ...
    def path(self, key: str) -> Path: ...
    def delete(self, key: str) -> None: ...


class LocalPrivateStorage:
    def __init__(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)
        self.root = (root / uuid4().hex).resolve()
        self.root.mkdir()
        # Prior-process orphan cleanup is local and opportunistic, not a durable worker.
        # Never follow symlinks or traverse arbitrary directories.
        cutoff = time.time() - 3600
        for run in root.iterdir():
            if (run != self.root and re.fullmatch(r"[a-f0-9]{32}", run.name)
                    and run.is_dir() and not run.is_symlink() and run.stat().st_mtime < cutoff):
                shutil.rmtree(run)

    def allocate(self, suffix: str = "") -> str:
        if suffix not in {"", ".xlsx", ".pdf", ".md"}:
            raise ValueError("Unsupported internal suffix")
        return uuid4().hex + suffix

    def path(self, key: str) -> Path:
        if not re.fullmatch(r"[a-f0-9]{32}(?:\.(?:xlsx|pdf|md))?", key):
            raise ValueError("Invalid internal object key")
        path = self.root / key
        if path.is_symlink() or path.resolve().parent != self.root:
            raise ValueError("Invalid internal object path")
        return path

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)
