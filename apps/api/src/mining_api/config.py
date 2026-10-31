"""Explicit environment configuration; never reads a dotenv file."""

import os
import re
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    environment: Literal["development", "test", "production"] = "development"
    frontend_origin: str = "http://localhost:3000"
    allowed_hosts: tuple[str, ...] = ("127.0.0.1", "localhost")
    proxy_secret: SecretStr
    cookie_secure: bool = True
    session_ttl_seconds: int = Field(default=3600, ge=60, le=86400)
    report_ttl_seconds: int = Field(default=3600, ge=300, le=3600)
    runtime_dir: Path = Path(__file__).resolve().parents[4] / ".runtime" / "private"

    @model_validator(mode="after")
    def validate_boundary(self):
        origin = urlsplit(self.frontend_origin)
        try:
            origin.port
        except ValueError:
            raise ValueError("Frontend origin has an invalid port") from None
        if (origin.scheme not in {"http", "https"} or not origin.hostname
                or origin.path or origin.query or origin.fragment or origin.username
                or origin.password or origin.netloc != origin.netloc.lower()):
            raise ValueError("Frontend origin must be an exact HTTP(S) origin")
        if not self.allowed_hosts or any(
            host not in {"localhost", "127.0.0.1"} for host in self.allowed_hosts
        ):
            raise ValueError("Local foundation requires explicit loopback hosts")
        if not re.fullmatch(r"[A-Za-z0-9_-]{32,256}", self.proxy_secret.get_secret_value()):
            raise ValueError("Proxy secret must contain 32 to 256 URL-safe ASCII characters")
        if self.environment == "production":
            raise ValueError("In-memory session foundation cannot run in production")
        allowed_root = Path(__file__).resolve().parents[4] / ".runtime"
        if not self.runtime_dir.resolve().is_relative_to(allowed_root.resolve()):
            raise ValueError("Local storage must remain under the repository runtime directory")
        if not self.cookie_secure and not (
            self.environment in {"development", "test"}
            and origin.scheme == "http"
            and origin.hostname in {"localhost", "127.0.0.1"}
        ):
            raise ValueError("Insecure cookies require explicit local HTTP development")
        return self

    @classmethod
    def from_environment(cls):
        # Explicit allowlist: no dotenv, developer secrets, or unrelated settings are read.
        mapping = {
            "API_ENV": "environment", "API_FRONTEND_ORIGIN": "frontend_origin",
            "API_PROXY_SECRET": "proxy_secret", "API_COOKIE_SECURE": "cookie_secure",
            "API_SESSION_TTL_SECONDS": "session_ttl_seconds",
            "API_REPORT_TTL_SECONDS": "report_ttl_seconds",
        }
        return cls(**{field: os.environ[key] for key, field in mapping.items() if key in os.environ})
