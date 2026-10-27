"""Read settings from environment variables.

The OpenAI API key belongs in the .env file, never in source code.
The page still opens when the key is missing. Generating a study pack
asks for the key at that moment.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Read .env if it exists. If it does not, the app still starts.
load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DATABASE = _PROJECT_ROOT / "data" / "studymaster.db"


@dataclass(frozen=True)
class Settings:
    """Settings loaded once from the environment."""

    openai_api_key: str | None
    openai_model: str
    fetch_timeout_seconds: float
    max_response_bytes: int
    max_source_chars: int
    min_source_chars: int
    database_path: Path
    openai_timeout_seconds: float
    openai_temperature: float
    require_login: bool = False


def get_settings() -> Settings:
    """Return the current settings.

    An empty OPENAI_API_KEY becomes None. The key value is never logged.
    """
    raw_key = _setting("OPENAI_API_KEY")
    model = _setting("OPENAI_MODEL") or "gpt-4o-mini"
    return Settings(
        openai_api_key=raw_key or None,
        openai_model=model,
        fetch_timeout_seconds=float(_positive_int("FETCH_TIMEOUT_SECONDS", 10)),
        max_response_bytes=_positive_int("MAX_RESPONSE_BYTES", 1_000_000),
        max_source_chars=_positive_int("MAX_SOURCE_CHARS", 60_000),
        min_source_chars=_positive_int("MIN_SOURCE_CHARS", 400),
        database_path=_database_path(),
        openai_timeout_seconds=float(_positive_int("OPENAI_TIMEOUT_SECONDS", 60)),
        openai_temperature=_non_negative_float("OPENAI_TEMPERATURE", 0.2),
        require_login=_require_login(),
    )


def _setting(name: str) -> str:
    """Read one setting from the environment, then from the host secret store.

    The value is never logged. A missing secret file leaves the setting blank.
    """
    raw = os.getenv(name, "").strip()
    if raw:
        return raw
    try:
        import streamlit as st

        value = st.secrets[name]
    except Exception:
        return ""
    return str(value).strip()


def _require_login() -> bool:
    """Return whether the page must hide packs until a login matches."""
    return _setting("REQUIRE_LOGIN").casefold() in {"1", "true", "yes"}


def _database_path() -> Path:
    """Return the SQLite file path from the environment, or the project default."""
    raw = _setting("DATABASE_PATH")
    if not raw:
        return _DEFAULT_DATABASE
    return Path(raw)


def _positive_int(name: str, default: int) -> int:
    """Read a positive integer setting, or keep the default."""
    raw = _setting(name)
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value <= 0:
        return default
    return value


def _non_negative_float(name: str, default: float) -> float:
    """Read a zero-or-higher decimal setting, or keep the default."""
    raw = _setting(name)
    if not raw:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    if value < 0:
        return default
    return value
