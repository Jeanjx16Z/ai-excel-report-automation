"""Environment configuration for optional Gemini reporting."""

from __future__ import annotations

import os


DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


def load_environment() -> None:
    """Load a local .env file when python-dotenv is installed."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        return
    load_dotenv()


def get_gemini_api_key() -> str:
    """Return the configured API key without logging or exposing it."""
    load_environment()
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not configured. Set it in the environment or .env file."
        )
    return api_key


def get_gemini_model() -> str:
    """Return the optional model override or the project default."""
    load_environment()
    return os.getenv("GEMINI_MODEL", DEFAULT_GEMINI_MODEL).strip() or DEFAULT_GEMINI_MODEL
