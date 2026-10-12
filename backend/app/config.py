"""Settings from environment variables, with an optional backend/.env file (never committed).

Secrets are only ever read here and passed to the client that needs them; they are never logged,
returned by the API, or included in error messages.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


def _load_env_file(path: Path = ENV_FILE) -> None:
    """Minimal .env reader (KEY=VALUE lines). Real environment variables take precedence."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_model: str
    llm_enabled: bool
    ingest_token: str
    imap_host: str | None
    imap_user: str | None
    imap_password: str | None

    @property
    def imap_configured(self) -> bool:
        return bool(self.imap_host and self.imap_user and self.imap_password)


def load_settings() -> Settings:
    _load_env_file()
    key = os.environ.get("DEEPSEEK_API_KEY") or None
    return Settings(
        deepseek_api_key=key,
        deepseek_base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
        deepseek_model=os.environ.get("DEEPSEEK_MODEL", "deepseek-flash"),
        llm_enabled=bool(key) and os.environ.get("SATHI_LLM_ENABLED", "1") != "0",
        ingest_token=os.environ.get("SATHI_INGEST_TOKEN", "demo-ingest"),
        imap_host=os.environ.get("SATHI_IMAP_HOST") or None,
        imap_user=os.environ.get("SATHI_IMAP_USER") or None,
        imap_password=os.environ.get("SATHI_IMAP_PASSWORD") or None,
    )
